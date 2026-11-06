import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings
from app.errors import ApiError
from app.models import User

settings = get_settings()

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

COMMON_PASSWORDS = {
    "password123",
    "1234567890",
    "qwertyuiop",
    "passwordpassword",
    "letmein123",
    "iloveyou123",
}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def validate_password(password: str) -> None:
    if len(password) < 10:
        raise ApiError(
            422,
            "weak_password",
            "Password minimal 10 karakter.",
            {"min_length": 10},
        )
    if len(password) > 128:
        raise ApiError(422, "weak_password", "Password maksimal 128 karakter.")
    if password.strip().lower() in COMMON_PASSWORDS:
        raise ApiError(422, "weak_password", "Password terlalu umum. Pilih yang lain.")


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.session_ttl_days)


def set_session_cookie(response: Any, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie,
        value=token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain_value,
        path="/",
    )


def clear_session_cookie(response: Any) -> None:
    response.delete_cookie(
        key=settings.session_cookie,
        path="/",
        domain=settings.cookie_domain_value,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def client_ip(request: Any) -> str | None:
    if request.client is None:
        return None
    import ipaddress

    try:
        return str(ipaddress.ip_address(request.client.host))
    except ValueError:
        return None


def audit_row(action: str, user_id: uuid.UUID | None, request: Any, **meta: Any) -> Any:
    from app.models import AuditLog

    return AuditLog(
        user_id=user_id,
        action=action,
        metadata_json=meta,
        ip=client_ip(request),
    )


def user_public_id(user: User) -> str:
    return str(user.id)
