import math
from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Favorite, MediaItem, MediaStatus, User, WatchHistory
from app.schemas.media import RecommendationOut
from app.services.media_serializer import thumbnail_url

router = APIRouter(tags=["recommendations"])

REASON_LABELS = {
    "recently_added": "Baru di perpustakaanmu",
    "same_category": "Karena kamu menyukai kategori ini",
    "because_favorited": "Karena kamu memfavoritkan kategori ini",
}


@router.get("/recommendations", response_model=list[RecommendationOut])
async def recommendations(
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RecommendationOut]:
    watched_rows = (
        await db.execute(
            select(MediaItem.id, MediaItem.category)
            .join(WatchHistory, WatchHistory.media_item_id == MediaItem.id)
            .where(WatchHistory.user_id == user.id)
        )
    ).all()
    favorite_rows = (
        await db.execute(
            select(MediaItem.id, MediaItem.category)
            .join(Favorite, Favorite.media_item_id == MediaItem.id)
            .where(Favorite.user_id == user.id)
        )
    ).all()

    watched_ids = {row[0] for row in watched_rows}
    category_counts: Counter[str] = Counter()
    for _, category in [*watched_rows, *favorite_rows]:
        if category:
            category_counts[category] += 1

    candidates = (
        await db.execute(
            select(MediaItem)
            .where(
                MediaItem.user_id == user.id,
                MediaItem.deleted_at.is_(None),
                MediaItem.status == MediaStatus.ready,
            )
            .order_by(MediaItem.created_at.desc())
            .limit(200)
        )
    ).scalars().all()

    scored: list[tuple[float, MediaItem, str]] = []
    for item in candidates:
        if item.id in watched_ids:
            continue
        if category_counts and item.category:
            affinity = category_counts[item.category] / max(sum(category_counts.values()), 1)
        else:
            affinity = 0.0
        age_days = 0.0
        if item.created_at:
            age_days = max(
                (candidates[0].created_at - item.created_at).total_seconds() / 86400, 0
            )
        recency = math.exp(-age_days / 30)
        favorite_bonus = 0.15 if item.category in {
            category for _, category in favorite_rows if category
        } else 0.0
        score = 0.55 * affinity + 0.3 * recency + favorite_bonus
        if category_counts:
            reason = "same_category"
        else:
            reason = "recently_added"
            score = recency
        scored.append((score, item, reason))

    scored.sort(key=lambda entry: entry[0], reverse=True)
    selected: list[RecommendationOut] = []
    per_category: Counter[str] = Counter()
    for score, item, reason in scored:
        if item.category and per_category[item.category] >= 6:
            continue
        per_category[item.category or "Lainnya"] += 1
        selected.append(
            RecommendationOut(
                media_id=item.id,
                title=item.title,
                category=item.category,
                thumbnail_url=thumbnail_url(item.id),
                reason=reason,
                reason_label=REASON_LABELS[reason],
                score=round(score, 4),
            )
        )
        if len(selected) >= limit:
            break
    return selected
