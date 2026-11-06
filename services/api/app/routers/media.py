import asyncio
import hashlib
import mimetypes
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import ApiError
from app.models import (
    Collection,
    CollectionItem,
    Favorite,
    FileRole,
    MediaFile,
    MediaItem,
    MediaKind,
    MediaStatus,
    User,
)
from app.schemas.media import MediaListOut, MediaOut, MediaPatch
from app.services.media_serializer import serialize_media
from app.services.quota import storage_usage
from app.services.storage import get_storage

router = APIRouter(prefix="/media", tags=["media"])
settings = get_settings()


def _sniff_media(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp":
        return "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    if head.startswith(b"OggS"):
        return "video/ogg"
    return None


def _process_image(source: Path, thumbnail: Path) -> tuple[int, int]:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        image.thumbnail((640, 640))
        if image.mode in {"RGBA", "LA", "P"}:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.split()[-1])
            image = background
        else:
            image = image.convert("RGB")
        thumbnail.parent.mkdir(parents=True, exist_ok=True)
        image.save(thumbnail, "JPEG", quality=82)
        return width, height


async def _get_owned(db: AsyncSession, user_id: uuid.UUID, media_id: uuid.UUID) -> MediaItem:
    item = await db.scalar(
        select(MediaItem).where(
            MediaItem.id == media_id,
            MediaItem.user_id == user_id,
            MediaItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise ApiError(404, "not_found", "Media tidak ditemukan.")
    return item


@router.get("", response_model=MediaListOut)
async def list_media(
    kind: str | None = Query(default=None),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    favorite: bool = Query(default=False),
    collection: uuid.UUID | None = Query(default=None),
    sort: str = Query(default="recent"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaListOut:
    conditions = [
        MediaItem.user_id == user.id,
        MediaItem.deleted_at.is_(None),
        MediaItem.status == MediaStatus.ready,
    ]
    if kind:
        try:
            conditions.append(MediaItem.kind == MediaKind(kind))
        except ValueError as exc:
            raise ApiError(422, "validation_error", "Kind tidak dikenal.") from exc
    if category:
        conditions.append(MediaItem.category == category)
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(MediaItem.title.ilike(pattern), MediaItem.description.ilike(pattern))
        )
    if favorite:
        conditions.append(
            MediaItem.id.in_(
                select(Favorite.media_item_id).where(Favorite.user_id == user.id)
            )
        )
    if collection:
        owned_collection = await db.scalar(
            select(Collection.id).where(
                Collection.id == collection, Collection.user_id == user.id
            )
        )
        if owned_collection is None:
            raise ApiError(404, "not_found", "Koleksi tidak ditemukan.")
        conditions.append(
            MediaItem.id.in_(
                select(CollectionItem.media_item_id).where(
                    CollectionItem.collection_id == collection
                )
            )
        )

    total = await db.scalar(select(func.count(MediaItem.id)).where(*conditions)) or 0

    if sort == "title":
        order = MediaItem.title.asc()
    elif sort == "duration":
        order = MediaItem.duration_seconds.desc().nullslast()
    else:
        order = MediaItem.created_at.desc()

    rows = (
        await db.execute(
            select(MediaItem)
            .where(*conditions)
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    items = await serialize_media(db, user.id, list(rows))
    return MediaListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/{media_id}", response_model=MediaOut)
async def get_media(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    item = await _get_owned(db, user.id, media_id)
    items = await serialize_media(db, user.id, [item])
    return MediaOut(**items[0])


@router.patch("/{media_id}", response_model=MediaOut)
async def patch_media(
    media_id: uuid.UUID,
    payload: MediaPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    item = await _get_owned(db, user.id, media_id)
    if payload.title is not None:
        item.title = payload.title.strip()
    if payload.category is not None:
        item.category = payload.category
        item.category_locked = True
    item.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(item)
    items = await serialize_media(db, user.id, [item])
    return MediaOut(**items[0])


@router.delete("/{media_id}")
async def delete_media(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    item = await _get_owned(db, user.id, media_id)
    files = (
        await db.execute(select(MediaFile).where(MediaFile.media_item_id == item.id))
    ).scalars().all()
    storage = get_storage()
    for media_file in files:
        try:
            storage.delete(media_file.storage_key)
        except Exception:
            pass
        await db.delete(media_file)
    item.deleted_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}


@router.get("/{media_id}/stream")
async def stream_media(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    await _get_owned(db, user.id, media_id)
    media_file = await db.scalar(
        select(MediaFile).where(
            MediaFile.media_item_id == media_id,
            MediaFile.role == FileRole.original,
        )
    )
    if media_file is None:
        raise ApiError(404, "not_found", "File media tidak tersedia.")
    storage = get_storage()
    path = storage.path_for(media_file.storage_key)
    if not path.exists():
        raise ApiError(404, "not_found", "File media hilang dari storage.")
    return FileResponse(
        path,
        media_type=media_file.mime_type,
        filename=None,
        content_disposition_type="inline",
    )


@router.get("/{media_id}/thumbnail")
async def media_thumbnail(
    media_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    await _get_owned(db, user.id, media_id)
    media_file = await db.scalar(
        select(MediaFile).where(
            MediaFile.media_item_id == media_id,
            MediaFile.role == FileRole.thumbnail,
        )
    )
    if media_file is None:
        raise ApiError(404, "not_found", "Thumbnail tidak tersedia.")
    storage = get_storage()
    path = storage.path_for(media_file.storage_key)
    if not path.exists():
        raise ApiError(404, "not_found", "Thumbnail hilang dari storage.")
    return FileResponse(path, media_type=media_file.mime_type)


@router.post("/upload", status_code=201, response_model=MediaOut)
async def upload_media(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    category: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    storage = get_storage()
    temp_dir = storage.root / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"upload-{uuid.uuid4().hex}.part"

    digest = hashlib.sha256()
    size = 0
    head = b""
    try:
        with temp_path.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                if not head:
                    head = chunk[:64]
                size += len(chunk)
                if size > settings.max_download_bytes:
                    raise ApiError(413, "too_large", "File melebihi batas unggah.")
                digest.update(chunk)
                handle.write(chunk)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if size == 0:
        temp_path.unlink(missing_ok=True)
        raise ApiError(422, "unsupported_media", "File kosong.")

    mime_type = _sniff_media(head)
    if mime_type is None:
        temp_path.unlink(missing_ok=True)
        raise ApiError(415, "unsupported_media", "Format file tidak didukung.")

    checksum = digest.hexdigest()
    duplicate = await db.scalar(
        select(MediaFile.media_item_id)
        .join(MediaItem, MediaItem.id == MediaFile.media_item_id)
        .where(
            MediaItem.user_id == user.id,
            MediaItem.deleted_at.is_(None),
            MediaFile.checksum_sha256 == checksum,
        )
    )
    if duplicate:
        temp_path.unlink(missing_ok=True)
        raise ApiError(
            409,
            "conflict_duplicate",
            "File yang sama sudah ada di perpustakaan.",
            {"media_id": str(duplicate)},
        )

    used = await storage_usage(db, user.id)
    if used + size > settings.user_quota_bytes:
        temp_path.unlink(missing_ok=True)
        raise ApiError(507, "storage_quota_exceeded", "Kuota penyimpanan tidak cukup.")

    kind = MediaKind.video if mime_type.startswith("video/") else MediaKind.image
    fallback_title = Path(file.filename or "media").stem.replace("_", " ").strip() or "Media"
    item = MediaItem(
        user_id=user.id,
        source_url=f"upload://{file.filename or 'file'}",
        canonical_url=f"upload://{checksum}",
        kind=kind,
        title=(title or fallback_title)[:200],
        category=category,
        status=MediaStatus.processing,
    )
    db.add(item)
    await db.flush()

    extension = mimetypes.guess_extension(mime_type) or ".bin"
    folder = "videos" if kind is MediaKind.video else "images"
    now = datetime.now(UTC)
    key = f"u_{user.id.hex}/{folder}/{now:%Y/%m}/{item.id}/original{extension}"
    storage.move_in(key, temp_path)
    db.add(
        MediaFile(
            media_item_id=item.id,
            role=FileRole.original,
            storage_driver="local",
            storage_key=key,
            mime_type=mime_type,
            bytes=size,
            checksum_sha256=checksum,
        )
    )

    if kind is MediaKind.image:
        try:
            thumbnail_key = key.rsplit("/", 1)[0] + "/thumb.jpg"
            width, height = await asyncio.to_thread(
                _process_image,
                storage.path_for(key),
                storage.path_for(thumbnail_key),
            )
            item.width = width
            item.height = height
            db.add(
                MediaFile(
                    media_item_id=item.id,
                    role=FileRole.thumbnail,
                    storage_driver="local",
                    storage_key=thumbnail_key,
                    mime_type="image/jpeg",
                    bytes=storage.size(thumbnail_key),
                )
            )
        except Exception:
            pass

    item.status = MediaStatus.ready
    item.updated_at = now
    await db.commit()
    await db.refresh(item)
    items = await serialize_media(db, user.id, [item])
    return MediaOut(**items[0])
