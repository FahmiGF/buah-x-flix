from datetime import UTC, datetime

from fastapi import Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import ApiError
from app.models import User, UserSession
from app.services.ratelimit import InMemoryRateLimiter, enforce
from app.services.security import (
    audit_row,
    clear_session_cookie,
    hash_password,
    hash_token,
    new_session_token,
    password_needs_rehash,
    session_expiry,
    set_session_cookie,
    validate_password,
    verify_password,
)

settings = get_settings()

# Per-IP and per-email buckets, mirroring the blueprint's two login limits.
login_ip_limiter = InMemoryRateLimiter(settings.login_rate_limit, 60)
login_email_limiter = InMemoryRateLimiter(settings.login_email_rate_limit, 60)


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    statement = select(User).where(
        func.lower(User.email) == email.strip().lower(),
        User.deleted_at.is_(None),
    )
    return (await db.execute(statement)).scalar_one_or_none()


async def _issue_session(
    db: AsyncSession, user: User, request: Request, response: Response
) -> None:
    token = new_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=session_expiry(),
            user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        )
    )
    set_session_cookie(response, token)


async def register(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    request: Request,
    response: Response,
) -> User:
    validate_password(password)
    normalized_email = email.strip().lower()
    display_name = display_name.strip()
    if not display_name:
        raise ApiError(422, "validation_error", "Nama tampilan wajib diisi.")

    if await find_user_by_email(db, normalized_email):
        raise ApiError(409, "conflict_duplicate", "Email sudah terdaftar.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(409, "conflict_duplicate", "Email sudah terdaftar.") from exc

    await _issue_session(db, user, request, response)
    db.add(audit_row("auth.register", user.id, request))
    await db.commit()
    await db.refresh(user)
    return user


async def login(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    request: Request,
    response: Response,
) -> User:
    normalized_email = email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    enforce(login_ip_limiter, f"ip:{ip}")
    enforce(login_email_limiter, f"email:{normalized_email}")

    user = await find_user_by_email(db, normalized_email)
    if user is None or not verify_password(user.password_hash, password):
        raise ApiError(401, "invalid_credentials", "Email atau password salah.")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_login_at = datetime.now(UTC)
    await _issue_session(db, user, request, response)
    db.add(audit_row("auth.login", user.id, request))
    await db.commit()
    await db.refresh(user)
    return user


async def logout(db: AsyncSession, request: Request, response: Response) -> None:
    token = request.cookies.get(settings.session_cookie)
    if token:
        await db.execute(
            update(UserSession)
            .where(UserSession.token_hash == hash_token(token), UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await db.commit()
    clear_session_cookie(response)
