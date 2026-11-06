from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, StorageUsage, UserOut
from app.services import auth as auth_service
from app.services.quota import storage_usage

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


async def build_user_out(db: AsyncSession, user: User) -> UserOut:
    used = await storage_usage(db, user.id)
    limit = settings.user_quota_bytes
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        storage=StorageUsage(
            used_bytes=used,
            limit_bytes=limit,
            percent=round(min(used / limit * 100, 100), 2) if limit else 0.0,
        ),
    )


@router.post("/register", status_code=201, response_model=UserOut)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await auth_service.register(
        db,
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
        request=request,
        response=response,
    )
    return await build_user_out(db, user)


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await auth_service.login(
        db,
        email=str(payload.email),
        password=payload.password,
        request=request,
        response=response,
    )
    return await build_user_out(db, user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    await auth_service.logout(db, request, response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return await build_user_out(db, user)
