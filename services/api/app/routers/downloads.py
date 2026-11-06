import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_db
from app.deps import get_current_user
from app.errors import ApiError
from app.models import (
    DownloadJob,
    JobState,
    MediaItem,
    MediaKind,
    MediaStatus,
    SourcePolicy,
    User,
)
from app.schemas.media import DownloadCreate, DownloadOut
from app.services import downloader
from app.services.analyzer import cache_entry, find_source
from app.services.safe_fetch import normalize_url

router = APIRouter(prefix="/downloads", tags=["downloads"])


def serialize_job(job: DownloadJob) -> DownloadOut:
    progress = 0
    if job.bytes_total:
        progress = min(int(job.bytes_done / job.bytes_total * 100), 100)
    return DownloadOut(
        id=job.id,
        state=job.state.value,
        url=job.url,
        bytes_total=job.bytes_total,
        bytes_done=job.bytes_done,
        progress=progress,
        error_code=job.error_code,
        error_message=job.error_message,
        media_id=job.media_item_id,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


async def _owned_job(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> DownloadJob:
    job = await db.scalar(
        select(DownloadJob).where(
            DownloadJob.id == job_id, DownloadJob.user_id == user_id
        )
    )
    if job is None:
        raise ApiError(404, "not_found", "Job unduhan tidak ditemukan.")
    return job


@router.post("", status_code=202, response_model=DownloadOut)
async def create_download(
    payload: DownloadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DownloadOut:
    normalized = normalize_url(payload.url)
    host = urlsplit(normalized).hostname or ""
    source = await find_source(db, host)
    if source is None:
        raise ApiError(
            403,
            "source_pending_review",
            "Sumber ini belum disetujui untuk diunduh.",
            {"host": host},
        )
    if source.policy is SourcePolicy.blocked:
        raise ApiError(403, "source_blocked", "Sumber ini diblokir.")
    if source.policy is SourcePolicy.embed_only:
        raise ApiError(
            403,
            "source_embed_only",
            "Sumber ini hanya boleh diputar lewat embed, tidak diunduh.",
        )
    if source.policy is not SourcePolicy.download_allowed:
        raise ApiError(
            403,
            "source_pending_review",
            "Sumber ini belum disetujui untuk diunduh.",
            {"host": host},
        )

    analysis = None
    if payload.analysis_id:
        try:
            analysis = cache_entry(payload.analysis_id, user.id)
        except ApiError:
            analysis = None

    title = payload.title or (
        analysis.response.title if analysis else None
    ) or "Media"
    kind = MediaKind.video
    if analysis and analysis.response.kind in {"video", "image"}:
        kind = MediaKind(analysis.response.kind)
    category = payload.category or None

    existing = await db.scalar(
        select(MediaItem.id).where(
            MediaItem.user_id == user.id,
            MediaItem.canonical_url == normalized,
            MediaItem.deleted_at.is_(None),
        )
    )
    if existing:
        raise ApiError(
            409,
            "conflict_duplicate",
            "Media ini sudah ada di perpustakaan.",
            {"media_id": str(existing)},
        )

    url_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    active = await db.scalar(
        select(DownloadJob.id).where(
            DownloadJob.user_id == user.id,
            DownloadJob.url_hash == url_hash,
            DownloadJob.state.in_(downloader.ACTIVE_STATES),
        )
    )
    if active:
        raise ApiError(
            409,
            "conflict_duplicate",
            "Unduhan untuk URL ini sedang berjalan.",
            {"job_id": str(active)},
        )

    item = MediaItem(
        user_id=user.id,
        source_id=source.id,
        source_url=normalized,
        canonical_url=normalized,
        kind=kind,
        title=title[:200],
        category=category,
        status=MediaStatus.processing,
    )
    db.add(item)
    await db.flush()

    job = DownloadJob(
        user_id=user.id,
        media_item_id=item.id,
        source_id=source.id,
        url=normalized,
        url_hash=url_hash,
        state=JobState.queued,
        idempotency_key=None,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    downloader.schedule(job.id)
    return serialize_job(job)


@router.get("", response_model=list[DownloadOut])
async def list_downloads(
    state: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DownloadOut]:
    statement = select(DownloadJob).where(DownloadJob.user_id == user.id)
    if state:
        try:
            statement = statement.where(DownloadJob.state == JobState(state))
        except ValueError as exc:
            raise ApiError(422, "validation_error", "State tidak dikenal.") from exc
    statement = statement.order_by(DownloadJob.created_at.desc()).limit(limit)
    rows = (await db.execute(statement)).scalars().all()
    return [serialize_job(job) for job in rows]


@router.get("/events")
async def download_events(
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    async def generator():
        for _ in range(300):
            async with SessionLocal() as db:
                rows = (
                    await db.execute(
                        select(DownloadJob)
                        .where(DownloadJob.user_id == user.id)
                        .order_by(DownloadJob.created_at.desc())
                        .limit(30)
                    )
                ).scalars().all()
                payload = [serialize_job(job).model_dump(mode="json") for job in rows]
            yield f"event: snapshot\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{job_id}", response_model=DownloadOut)
async def get_download(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DownloadOut:
    job = await _owned_job(db, user.id, job_id)
    return serialize_job(job)


@router.delete("/{job_id}")
async def cancel_download(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    job = await _owned_job(db, user.id, job_id)
    if not downloader.is_active(job.state):
        raise ApiError(409, "job_not_cancellable", "Job sudah selesai dan tidak bisa dibatalkan.")
    downloader.request_cancel(job.id)
    job.state = JobState.cancelled
    job.finished_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}


@router.post("/{job_id}/retry", response_model=DownloadOut)
async def retry_download(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DownloadOut:
    job = await _owned_job(db, user.id, job_id)
    if job.state not in {JobState.failed, JobState.blocked}:
        raise ApiError(409, "job_not_cancellable", "Hanya job gagal yang bisa diulang.")
    job.state = JobState.queued
    job.error_code = None
    job.error_message = None
    job.bytes_done = 0
    job.attempts = 0
    job.finished_at = None
    await db.commit()
    downloader.schedule(job.id)
    return serialize_job(job)
