import re
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.errors import ApiError
from app.models import Collection, CollectionItem, MediaItem, MediaStatus, User
from app.schemas.media import (
    CollectionCreate,
    CollectionDetail,
    CollectionItemIn,
    CollectionOut,
    MediaOut,
)
from app.services.media_serializer import serialize_media

router = APIRouter(prefix="/collections", tags=["collections"])


def _slugify(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return value[:60] or "koleksi"


async def _owned_collection(
    db: AsyncSession, user_id: uuid.UUID, collection_id: uuid.UUID
) -> Collection:
    collection = await db.scalar(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user_id
        )
    )
    if collection is None:
        raise ApiError(404, "not_found", "Koleksi tidak ditemukan.")
    return collection


async def _collection_out(db: AsyncSession, collection: Collection) -> CollectionOut:
    count = await db.scalar(
        select(func.count(CollectionItem.media_item_id)).where(
            CollectionItem.collection_id == collection.id
        )
    )
    return CollectionOut(
        id=collection.id,
        title=collection.title,
        slug=collection.slug,
        description=collection.description,
        item_count=count or 0,
        created_at=collection.created_at,
    )


@router.get("", response_model=list[CollectionOut])
async def list_collections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CollectionOut]:
    rows = (
        await db.execute(
            select(Collection)
            .where(Collection.user_id == user.id)
            .order_by(Collection.created_at.desc())
        )
    ).scalars().all()
    return [await _collection_out(db, collection) for collection in rows]


@router.post("", status_code=201, response_model=CollectionOut)
async def create_collection(
    payload: CollectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollectionOut:
    base = _slugify(payload.title)
    slug = base
    suffix = 2
    while await db.scalar(
        select(Collection.id).where(
            Collection.user_id == user.id, Collection.slug == slug
        )
    ):
        slug = f"{base}-{suffix}"
        suffix += 1
    collection = Collection(
        user_id=user.id,
        title=payload.title.strip(),
        slug=slug,
        description=payload.description,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return await _collection_out(db, collection)


@router.get("/{collection_id}", response_model=CollectionDetail)
async def get_collection(
    collection_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollectionDetail:
    collection = await _owned_collection(db, user.id, collection_id)
    base = await _collection_out(db, collection)
    rows = (
        await db.execute(
            select(MediaItem)
            .join(CollectionItem, CollectionItem.media_item_id == MediaItem.id)
            .where(
                CollectionItem.collection_id == collection.id,
                MediaItem.deleted_at.is_(None),
                MediaItem.status == MediaStatus.ready,
            )
            .order_by(CollectionItem.position.asc())
        )
    ).scalars().all()
    items = await serialize_media(db, user.id, list(rows))
    return CollectionDetail(
        **base.model_dump(), items=[MediaOut(**item) for item in items]
    )


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    collection = await _owned_collection(db, user.id, collection_id)
    await db.delete(collection)
    await db.commit()
    return {"ok": True}


@router.post("/{collection_id}/items", status_code=201)
async def add_collection_item(
    collection_id: uuid.UUID,
    payload: CollectionItemIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    collection = await _owned_collection(db, user.id, collection_id)
    media = await db.scalar(
        select(MediaItem).where(
            MediaItem.id == payload.media_id,
            MediaItem.user_id == user.id,
            MediaItem.deleted_at.is_(None),
        )
    )
    if media is None:
        raise ApiError(404, "not_found", "Media tidak ditemukan.")
    existing = await db.scalar(
        select(CollectionItem.media_item_id).where(
            CollectionItem.collection_id == collection.id,
            CollectionItem.media_item_id == media.id,
        )
    )
    if existing is None:
        position = (
            await db.scalar(
                select(func.coalesce(func.max(CollectionItem.position), 0)).where(
                    CollectionItem.collection_id == collection.id
                )
            )
            or 0
        ) + 1
        db.add(
            CollectionItem(
                collection_id=collection.id,
                media_item_id=media.id,
                position=position,
            )
        )
        await db.commit()
    return {"ok": True}


@router.delete("/{collection_id}/items/{media_id}")
async def remove_collection_item(
    collection_id: uuid.UUID,
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    collection = await _owned_collection(db, user.id, collection_id)
    await db.execute(
        delete(CollectionItem).where(
            CollectionItem.collection_id == collection.id,
            CollectionItem.media_item_id == media_id,
        )
    )
    await db.commit()
    return {"ok": True}
