from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.errors import ApiError
from app.models import Source, User
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer import analyze_url, cache_entry
from app.services.storage import get_storage

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    return await analyze_url(db, user.id, payload.url, payload.content_hint)


@router.get("/analyze/{analysis_id}/thumbnail")
async def analysis_thumbnail(
    analysis_id: str,
    user: User = Depends(get_current_user),
) -> Response:
    entry = cache_entry(analysis_id, user.id)
    if not entry.thumbnail_key:
        raise ApiError(404, "not_found", "Thumbnail tidak tersedia.")
    data = get_storage().read_bytes(entry.thumbnail_key)
    return Response(
        content=data,
        media_type=entry.thumbnail_type or "image/jpeg",
        headers={"Cache-Control": "private, max-age=1800"},
    )


@router.get("/sources")
async def list_sources(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = user
    rows = (await db.execute(select(Source).order_by(Source.host))).scalars().all()
    return {
        "items": [
            {
                "host": source.host,
                "display_name": source.display_name,
                "policy": source.policy.value,
                "max_file_bytes": source.max_file_bytes,
            }
            for source in rows
        ]
    }
