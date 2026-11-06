import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MediaFile, MediaItem


class QuotaExceeded(Exception):
    def __init__(self, used: int, incoming: int, limit: int) -> None:
        self.used = used
        self.incoming = incoming
        self.limit = limit
        super().__init__("storage quota exceeded")


async def storage_usage(db: AsyncSession, user_id: uuid.UUID) -> int:
    statement = (
        select(func.coalesce(func.sum(MediaFile.bytes), 0))
        .join(MediaItem, MediaItem.id == MediaFile.media_item_id)
        .where(MediaItem.user_id == user_id, MediaItem.deleted_at.is_(None))
    )
    value = await db.scalar(statement)
    return int(value or 0)


def ensure_quota(used: int, incoming: int, limit: int) -> None:
    if incoming < 0:
        raise ValueError("incoming bytes must not be negative")
    if used + incoming > limit:
        raise QuotaExceeded(used=used, incoming=incoming, limit=limit)
