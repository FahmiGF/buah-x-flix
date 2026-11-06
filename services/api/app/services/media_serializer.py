import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Favorite, FileRole, MediaFile, MediaItem, Source, WatchHistory


def thumbnail_url(media_id: uuid.UUID) -> str:
    return f"/api/v1/media/{media_id}/thumbnail"


def stream_url(media_id: uuid.UUID) -> str:
    return f"/api/v1/media/{media_id}/stream"


async def favorite_ids(
    db: AsyncSession, user_id: uuid.UUID, media_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    if not media_ids:
        return set()
    rows = await db.execute(
        select(Favorite.media_item_id).where(
            Favorite.user_id == user_id,
            Favorite.media_item_id.in_(media_ids),
        )
    )
    return set(rows.scalars().all())


async def watch_map(
    db: AsyncSession, user_id: uuid.UUID, media_ids: list[uuid.UUID]
) -> dict[uuid.UUID, WatchHistory]:
    if not media_ids:
        return {}
    rows = await db.execute(
        select(WatchHistory).where(
            WatchHistory.user_id == user_id,
            WatchHistory.media_item_id.in_(media_ids),
        )
    )
    return {row.media_item_id: row for row in rows.scalars().all()}


async def source_info(
    db: AsyncSession, items: list[MediaItem]
) -> dict[uuid.UUID, Source]:
    source_ids = {item.source_id for item in items if item.source_id}
    if not source_ids:
        return {}
    rows = await db.execute(select(Source).where(Source.id.in_(source_ids)))
    return {source.id: source for source in rows.scalars().all()}


async def has_thumbnail(db: AsyncSession, media_id: uuid.UUID) -> bool:
    row = await db.scalar(
        select(MediaFile.id).where(
            MediaFile.media_item_id == media_id,
            MediaFile.role == FileRole.thumbnail,
        )
    )
    return row is not None


async def serialize_media(
    db: AsyncSession, user_id: uuid.UUID, items: list[MediaItem]
) -> list[dict]:
    ids = [item.id for item in items]
    favorites = await favorite_ids(db, user_id, ids)
    watches = await watch_map(db, user_id, ids)
    sources = await source_info(db, items)
    thumbnails = {
        media_id
        for media_id in ids
        if await has_thumbnail(db, media_id)
    }

    output: list[dict] = []
    for item in items:
        watch = watches.get(item.id)
        source = sources.get(item.source_id) if item.source_id else None
        output.append(
            {
                "id": str(item.id),
                "title": item.title,
                "description": item.description,
                "kind": item.kind.value,
                "category": item.category,
                "duration_seconds": item.duration_seconds,
                "width": item.width,
                "height": item.height,
                "embed_url": item.embed_url,
                "thumbnail_url": thumbnail_url(item.id) if item.id in thumbnails else None,
                "stream_url": stream_url(item.id) if item.kind is not None else None,
                "source": {
                    "host": source.host if source else None,
                    "display_name": source.display_name if source else None,
                },
                "is_favorite": item.id in favorites,
                "progress": {
                    "position_seconds": watch.position_seconds if watch else 0,
                    "completed": watch.completed if watch else False,
                },
                "created_at": item.created_at.isoformat(),
            }
        )
    return output
