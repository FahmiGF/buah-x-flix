import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy import select, update

from app.config import get_settings
from app.db import SessionLocal
from app.errors import ApiError
from app.models import (
    DownloadJob,
    FileRole,
    JobState,
    MediaFile,
    MediaItem,
    MediaKind,
    MediaStatus,
    Source,
)
from app.services.quota import QuotaExceeded, ensure_quota, storage_usage
from app.services.safe_fetch import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    DownloadCancelled,
    download_to_temp,
)
from app.services.storage import get_storage

settings = get_settings()

ACTIVE_STATES = (
    JobState.queued,
    JobState.resolving,
    JobState.downloading,
    JobState.processing,
)

_BACKGROUND: set[asyncio.Task] = set()
_CANCEL: set[uuid.UUID] = set()


def schedule(job_id: uuid.UUID) -> None:
    task = asyncio.create_task(run_download_job(job_id))
    _BACKGROUND.add(task)
    task.add_done_callback(_BACKGROUND.discard)


def request_cancel(job_id: uuid.UUID) -> None:
    _CANCEL.add(job_id)


def is_active(state: JobState) -> bool:
    return state in ACTIVE_STATES


async def _set_job(job_id: uuid.UUID, **values: object) -> None:
    async with SessionLocal() as db:
        await db.execute(update(DownloadJob).where(DownloadJob.id == job_id).values(**values))
        await db.commit()


def _thumbnail_for_image(source: Path, destination: Path) -> tuple[int, int]:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        image.thumbnail((640, 640))
        if image.mode in {"RGBA", "LA", "P"}:
            background = Image.new("RGB", image.size, "white")
            background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
            image = background
        else:
            image = image.convert("RGB")
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "JPEG", quality=82)
        return width, height


async def _fail(job_id: uuid.UUID, code: str, message: str, temp: Path) -> None:
    await asyncio.to_thread(temp.unlink, missing_ok=True)
    async with SessionLocal() as db:
        job = await db.get(DownloadJob, job_id)
        if job is None:
            return
        if job.state == JobState.cancelled:
            return
        job.state = JobState.failed
        job.error_code = code
        job.error_message = message[:500]
        job.finished_at = datetime.now(UTC)
        if job.media_item_id:
            item = await db.get(MediaItem, job.media_item_id)
            if item and item.status == MediaStatus.processing:
                item.status = MediaStatus.failed
        await db.commit()


async def run_download_job(job_id: uuid.UUID) -> None:
    storage = get_storage()
    temp = storage.root / ".tmp" / f"{job_id}.part"
    await asyncio.to_thread(temp.parent.mkdir, parents=True, exist_ok=True)

    async with SessionLocal() as db:
        job = await db.get(DownloadJob, job_id)
        if job is None or job.state != JobState.queued:
            return
        source = await db.get(Source, job.source_id) if job.source_id else None
        item = await db.get(MediaItem, job.media_item_id) if job.media_item_id else None
        if item is None:
            await _fail(job_id, "internal_error", "Media item tidak ditemukan.", temp)
            return

        max_bytes = min(
            settings.max_download_bytes,
            source.max_file_bytes if source else settings.max_download_bytes,
        )
        job.state = JobState.resolving
        job.started_at = datetime.now(UTC)
        job.attempts += 1
        await db.commit()

        try:
            used = await storage_usage(db, job.user_id)
            if used >= settings.user_quota_bytes:
                raise ApiError(507, "storage_quota_exceeded", "Kuota penyimpanan penuh.")
            job.state = JobState.downloading
            await db.commit()

            async def on_progress(done: int, total: int | None) -> None:
                await _set_job(job_id, bytes_done=done, bytes_total=total)

            result = await download_to_temp(
                job.url,
                temp,
                max_bytes=max_bytes,
                on_progress=on_progress,
                should_cancel=lambda: job_id in _CANCEL,
            )
        except DownloadCancelled:
            temp.unlink(missing_ok=True)
            _CANCEL.discard(job_id)
            await _set_job(
                job_id,
                state=JobState.cancelled,
                finished_at=datetime.now(UTC),
            )
            return
        except QuotaExceeded as exc:
            await _fail(
                job_id,
                "storage_quota_exceeded",
                f"Kuota penyimpanan tidak cukup ({exc.used} + {exc.incoming} > {exc.limit}).",
                temp,
            )
            return
        except ApiError as exc:
            await _fail(job_id, exc.code, exc.message, temp)
            return
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            await _fail(job_id, "download_failed", str(exc), temp)
            return

    async with SessionLocal() as db:
        job = await db.get(DownloadJob, job_id)
        item = await db.get(MediaItem, job.media_item_id) if job and job.media_item_id else None
        if job is None or item is None:
            temp.unlink(missing_ok=True)
            return
        if job.state == JobState.cancelled:
            temp.unlink(missing_ok=True)
            return

        try:
            used = await storage_usage(db, job.user_id)
            ensure_quota(used, result.total_bytes, settings.user_quota_bytes)
        except QuotaExceeded as exc:
            await db.rollback()
            await _fail(
                job_id,
                "storage_quota_exceeded",
                f"Kuota penyimpanan tidak cukup ({exc.used} + {exc.incoming} > {exc.limit}).",
                temp,
            )
            return

        extension = result.extension
        kind = (
            MediaKind.video
            if result.content_type.startswith("video/") or extension in VIDEO_EXTENSIONS
            else MediaKind.image
            if result.content_type.startswith("image/") or extension in IMAGE_EXTENSIONS
            else item.kind
        )
        item.kind = kind
        item.status = MediaStatus.processing
        now = datetime.now(UTC)
        folder = "videos" if kind is MediaKind.video else "images"
        key = (
            f"u_{job.user_id.hex}/{folder}/{now:%Y/%m}/{item.id}/original{extension}"
        )
        storage.move_in(key, result.temp_path)

        db.add(
            MediaFile(
                media_item_id=item.id,
                role=FileRole.original,
                storage_driver="local",
                storage_key=key,
                mime_type=result.content_type or "application/octet-stream",
                bytes=result.total_bytes,
                checksum_sha256=result.checksum_sha256,
            )
        )

        if kind is MediaKind.image:
            try:
                thumbnail_source = storage.path_for(key)
                thumbnail_key = key.rsplit("/", 1)[0] + "/thumb.jpg"
                width, height = await asyncio.to_thread(
                    _thumbnail_for_image,
                    thumbnail_source,
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
        job.state = JobState.completed
        job.bytes_done = result.total_bytes
        job.bytes_total = result.total_bytes
        job.finished_at = now
        await db.commit()

    _CANCEL.discard(job_id)


async def sweep_stale_jobs() -> None:
    async with SessionLocal() as db:
        statement = (
            update(DownloadJob)
            .where(DownloadJob.state.in_(ACTIVE_STATES))
            .values(
                state=JobState.failed,
                error_code="worker_lost",
                error_message="Worker berhenti sebelum job selesai.",
                finished_at=datetime.now(UTC),
            )
        )
        await db.execute(statement)
        await db.commit()


async def job_media_id(job_id: uuid.UUID) -> uuid.UUID | None:
    async with SessionLocal() as db:
        return await db.scalar(
            select(DownloadJob.media_item_id).where(DownloadJob.id == job_id)
        )
