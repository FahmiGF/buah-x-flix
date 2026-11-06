from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.errors import ApiError
from app.models import User, UserSession
from app.services.security import hash_token

settings = get_settings()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        raise ApiError(401, "unauthorized", "Sesi tidak ditemukan. Silakan masuk.")

    statement = (
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > func.now(),
            User.deleted_at.is_(None),
        )
    )
    user = (await db.execute(statement)).scalar_one_or_none()
    if user is None:
        raise ApiError(401, "unauthorized", "Sesi sudah berakhir. Silakan masuk lagi.")
    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    try:
        return await get_current_user(request, db)
    except ApiError:
        return None
