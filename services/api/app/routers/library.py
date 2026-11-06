import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.errors import ApiError
from app.models import Favorite, MediaItem, MediaStatus, User, WatchHistory
from app.schemas.media import MediaOut, WatchHistoryIn, WatchHistoryOut
from app.services.media_serializer import serialize_media

router = APIRouter(tags=["library"])


async def _owned_media(db: AsyncSession, user_id: uuid.UUID, media_id: uuid.UUID) -> MediaItem:
    item = await db.scalar(
        select(MediaItem).where(
            MediaItem.id == media_id,
            MediaItem.user_id == user_id,
            MediaItem.deleted_at.is_(None),
            MediaItem.status == MediaStatus.ready,
        )
    )
    if item is None:
        raise ApiError(404, "not_found", "Media tidak ditemukan.")
    return item


@router.get("/favorites", response_model=list[MediaOut])
async def list_favorites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MediaOut]:
    rows = (
        await db.execute(
            select(MediaItem)
            .join(Favorite, Favorite.media_item_id == MediaItem.id)
            .where(
                Favorite.user_id == user.id,
                MediaItem.deleted_at.is_(None),
                MediaItem.status == MediaStatus.ready,
            )
            .order_by(Favorite.created_at.desc())
        )
    ).scalars().all()
    return [MediaOut(**item) for item in await serialize_media(db, user.id, list(rows))]


@router.put("/favorites/{media_id}")
async def add_favorite(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    await _owned_media(db, user.id, media_id)
    existing = await db.scalar(
        select(Favorite.media_item_id).where(
            Favorite.user_id == user.id, Favorite.media_item_id == media_id
        )
    )
    if existing is None:
        db.add(Favorite(user_id=user.id, media_item_id=media_id))
        await db.commit()
    return {"ok": True}


@router.delete("/favorites/{media_id}")
async def remove_favorite(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user.id, Favorite.media_item_id == media_id
        )
    )
    await db.commit()
    return {"ok": True}


@router.post("/watch-history", response_model=WatchHistoryOut)
async def upsert_watch_history(
    payload: WatchHistoryIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchHistoryOut:
    item = await _owned_media(db, user.id, payload.media_id)
    duration = payload.duration_seconds or item.duration_seconds
    position = max(payload.position_seconds, 0)
    if duration:
        position = min(position, duration)
    completed = bool(duration and position >= duration * 0.95)

    row = await db.scalar(
        select(WatchHistory).where(
            WatchHistory.user_id == user.id,
            WatchHistory.media_item_id == payload.media_id,
        )
    )
    now = datetime.now(UTC)
    if row is None:
        row = WatchHistory(
            user_id=user.id,
            media_item_id=payload.media_id,
            position_seconds=position,
            duration_seconds=duration,
            completed=completed,
            play_count=1,
            last_watched_at=now,
        )
        db.add(row)
    else:
        row.position_seconds = position
        row.duration_seconds = duration or row.duration_seconds
        row.completed = completed
        row.last_watched_at = now
    await db.commit()
    await db.refresh(row)
    return WatchHistoryOut(
        media_id=row.media_item_id,
        position_seconds=row.position_seconds,
        duration_seconds=row.duration_seconds,
        completed=row.completed,
        play_count=row.play_count,
        last_watched_at=row.last_watched_at,
    )


@router.get("/watch-history", response_model=list[MediaOut])
async def list_watch_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MediaOut]:
    rows = (
        await db.execute(
            select(MediaItem)
            .join(WatchHistory, WatchHistory.media_item_id == MediaItem.id)
            .where(
                WatchHistory.user_id == user.id,
                MediaItem.deleted_at.is_(None),
                MediaItem.status == MediaStatus.ready,
            )
            .order_by(WatchHistory.last_watched_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return [MediaOut(**item) for item in await serialize_media(db, user.id, list(rows))]


@router.get("/library/continue", response_model=list[MediaOut])
async def continue_watching(
    limit: int = Query(default=12, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MediaOut]:
    rows = (
        await db.execute(
            select(MediaItem)
            .join(WatchHistory, WatchHistory.media_item_id == MediaItem.id)
            .where(
                WatchHistory.user_id == user.id,
                WatchHistory.completed.is_(False),
                WatchHistory.position_seconds > 0,
                MediaItem.deleted_at.is_(None),
                MediaItem.status == MediaStatus.ready,
            )
            .order_by(WatchHistory.last_watched_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [MediaOut(**item) for item in await serialize_media(db, user.id, list(rows))]
