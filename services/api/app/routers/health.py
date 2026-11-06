from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.storage import get_storage

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    database = False
    try:
        await db.execute(text("select 1"))
        database = True
    except Exception:
        database = False

    storage = get_storage().ready()
    status = "ok" if database and storage else "degraded"
    return {
        "status": status,
        "checks": {"database": database, "storage": storage},
    }
