import re
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import ApiError
from app.models import Source, SourcePolicy
from app.schemas.analyze import (
    AnalyzeResponse,
    Candidate,
    DownloadPolicy,
    PlaybackInfo,
    SourceInfo,
)
from app.services import metadata as metadata_service
from app.services.safe_fetch import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    extension_for,
    fetch_limited,
    normalize_url,
    probe_media,
)
from app.services.storage import get_storage

settings = get_settings()

CACHE_TTL_SECONDS = 30 * 60
CACHE_MAX_ENTRIES = 200

CATEGORY_RULES: dict[str, list[str]] = {
    "Film": ["movie", "film", "trailer", "short film", "cinema"],
    "Dokumenter": ["documentary", "nature", "history", "wildlife"],
    "Edukasi": ["lecture", "course", "lesson", "explainer", "education", "science"],
    "Musik": ["music video", "live session", "concert", "album", "song"],
    "Olahraga": ["highlights", "match", "sport", "training", "goal"],
    "Hiburan": ["comedy", "vlog", "reaction", "podcast", "funny"],
    "Teknologi": ["tech", "programming", "software", " ai ", "gadget", "review", "code"],
    "Travel": ["travel", "drone", "destination", "city tour", "island"],
    "Gaming": ["gameplay", "speedrun", "walkthrough", "gaming", "game"],
    "Tutorial": ["how to", "tutorial", "guide", "step by step", "diy"],
}


@dataclass
class AnalysisEntry:
    user_id: uuid.UUID
    response: AnalyzeResponse
    thumbnail_key: str | None
    thumbnail_type: str | None
    created_at: float


_CACHE: OrderedDict[str, AnalysisEntry] = OrderedDict()


def _evict_cache() -> None:
    now = time.time()
    expired = [key for key, entry in _CACHE.items() if now - entry.created_at > CACHE_TTL_SECONDS]
    for key in expired:
        _CACHE.pop(key, None)
    while len(_CACHE) > CACHE_MAX_ENTRIES:
        _CACHE.popitem(last=False)


def cache_entry(analysis_id: str, user_id: uuid.UUID) -> AnalysisEntry:
    _evict_cache()
    entry = _CACHE.get(analysis_id)
    if entry is None or entry.user_id != user_id:
        raise ApiError(404, "not_found", "Hasil analisis tidak ditemukan atau sudah kedaluwarsa.")
    return entry


async def find_source(db: AsyncSession, host: str) -> Source | None:
    sources = (await db.execute(select(Source))).scalars().all()
    for source in sources:
        if host == source.host:
            return source
        if source.include_subdomains and host.endswith(f".{source.host}"):
            return source
    return None


def classify(title: str | None, description: str | None) -> tuple[str, float]:
    haystack = f" {title or ''} {description or ''} ".lower()
    best = ("Lainnya", 0.0)
    for category, keywords in CATEGORY_RULES.items():
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score:
            confidence = min(0.4 + score * 0.2, 0.95)
            if confidence > best[1]:
                best = (category, confidence)
    return best


def _title_from_url(url: str) -> str:
    name = unquote(Path(urlsplit(url).path).name)
    name = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", name)
    name = re.sub(r"[_+]+", " ", name).strip()
    return name or "Media tanpa judul"


def _source_info(host: str, source: Source | None) -> SourceInfo:
    return SourceInfo(
        host=host,
        display_name=source.display_name if source else host,
        policy=(source.policy if source else SourcePolicy.pending_review).value,
    )


def _download_policy(
    policy: SourcePolicy, kind: str, drm: bool, has_candidates: bool, max_bytes: int
) -> DownloadPolicy:
    if drm:
        return DownloadPolicy(allowed=False, reason="drm_protected", max_bytes=0)
    if policy is SourcePolicy.blocked:
        return DownloadPolicy(allowed=False, reason="source_blocked", max_bytes=0)
    if policy is SourcePolicy.embed_only:
        return DownloadPolicy(
            allowed=False, reason="source_embed_only", max_bytes=0
        )
    if policy is SourcePolicy.pending_review:
        return DownloadPolicy(
            allowed=False, reason="source_pending_review", max_bytes=0
        )
    if kind == "stream":
        return DownloadPolicy(
            allowed=False, reason="stream_not_supported", max_bytes=0
        )
    if not has_candidates:
        return DownloadPolicy(
            allowed=False, reason="no_downloadable_candidate", max_bytes=0
        )
    return DownloadPolicy(allowed=True, reason="source_download_allowed", max_bytes=max_bytes)


async def _cache_thumbnail(analysis_id: str, url: str | None) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    try:
        fetched = await fetch_limited(url, settings.analyzer_max_image_bytes)
    except Exception:
        return None, None
    if not fetched.content_type.startswith("image/"):
        return None, None
    extension = extension_for(fetched.content_type, fetched.url)
    key = f".cache/analyze/{analysis_id}{extension}"
    get_storage().save_bytes(key, fetched.content)
    return key, fetched.content_type


def _cache_put(entry: AnalysisEntry) -> None:
    _CACHE[entry.response.analysis_id] = entry
    _CACHE.move_to_end(entry.response.analysis_id)
    _evict_cache()


async def _finish(
    *,
    analysis_id: str,
    user_id: uuid.UUID,
    normalized: str,
    source_info: SourceInfo,
    source: Source | None,
    kind: str,
    title: str,
    description: str | None,
    duration: int | None,
    published: str | None,
    candidates: list[Candidate],
    thumbnail_source: str | None,
    playback: PlaybackInfo,
    drm: bool,
    warnings: list[str],
) -> AnalyzeResponse:
    thumbnail_key, thumbnail_type = await _cache_thumbnail(analysis_id, thumbnail_source)
    max_bytes = min(
        settings.max_download_bytes,
        source.max_file_bytes if source else settings.max_download_bytes,
    )
    policy = source.policy if source else SourcePolicy.pending_review
    category, confidence = classify(title, description)
    _ = category, confidence
    response = AnalyzeResponse(
        analysis_id=analysis_id,
        input_url=normalized,
        canonical_url=normalized,
        kind=kind,  # type: ignore[arg-type]
        source=source_info,
        title=title,
        description=description,
        duration_seconds=duration,
        thumbnail_url=(
            f"/api/v1/analyze/{analysis_id}/thumbnail" if thumbnail_key else None
        ),
        published_at=published,
        candidates=candidates,
        download=_download_policy(
            policy, kind, drm, bool(candidates), max_bytes
        ),
        playback=playback,
        warnings=warnings,
    )
    _cache_put(
        AnalysisEntry(
            user_id=user_id,
            response=response,
            thumbnail_key=thumbnail_key,
            thumbnail_type=thumbnail_type,
            created_at=time.time(),
        )
    )
    return response


def _dedupe(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
        if len(result) >= limit:
            break
    return result


async def analyze_url(
    db: AsyncSession,
    user_id: uuid.UUID,
    raw_url: str,
    content_hint: str = "auto",
) -> AnalyzeResponse:
    normalized = normalize_url(raw_url)
    host = urlsplit(normalized).hostname or ""
    source = await find_source(db, host)
    source_info = _source_info(host, source)
    analysis_id = uuid.uuid4().hex
    warnings: list[str] = []

    embed = metadata_service.embed_url_for(normalized)
    if embed:
        title = _title_from_url(normalized)
        description = None
        thumbnail = None
        try:
            fetched = await fetch_limited(normalized)
            page = metadata_service.extract_page_metadata(
                fetched.content.decode("utf-8", "ignore"), fetched.url
            )
            title = page.title or title
            description = page.description
            thumbnail = page.thumbnail_candidates[0] if page.thumbnail_candidates else None
        except ApiError:
            warnings.append("Metadata halaman tidak tersedia; memakai embed resmi.")
        return await _finish(
            analysis_id=analysis_id,
            user_id=user_id,
            normalized=normalized,
            source_info=source_info,
            source=source,
            kind="stream",
            title=title,
            description=description,
            duration=None,
            published=None,
            candidates=[],
            thumbnail_source=thumbnail,
            playback=PlaybackInfo(mode="embed", url=embed),
            drm=False,
            warnings=warnings,
        )

    suffix = Path(urlsplit(normalized).path).suffix.lower()
    fetched = None
    if suffix in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS or content_hint in {"video", "image"}:
        probe = await probe_media(normalized)
        if probe.content_type.startswith("video/") or probe.content_type.startswith("image/"):
            kind = "video" if probe.content_type.startswith("video/") else "image"
            title = _title_from_url(normalized)
            candidate = Candidate(
                url=probe.final_url,
                kind=kind,
                mime_type=probe.content_type,
                bytes=probe.total_bytes,
                label="Original",
            )
            thumbnail = probe.final_url if kind == "image" else None
            return await _finish(
                analysis_id=analysis_id,
                user_id=user_id,
                normalized=normalized,
                source_info=source_info,
                source=source,
                kind=kind,
                title=title,
                description=None,
                duration=None,
                published=None,
                candidates=[candidate],
                thumbnail_source=thumbnail,
                playback=PlaybackInfo(mode="file", url=probe.final_url),
                drm=False,
                warnings=warnings,
            )
        fetched = await fetch_limited(normalized)
    else:
        fetched = await fetch_limited(normalized)
        if fetched.content_type.startswith(("video/", "image/")):
            kind = "video" if fetched.content_type.startswith("video/") else "image"
            length_header = fetched.headers.get("content-length")
            size = int(length_header) if length_header and length_header.isdigit() else None
            candidate = Candidate(
                url=fetched.url,
                kind=kind,
                mime_type=fetched.content_type,
                bytes=size,
                label="Original",
            )
            return await _finish(
                analysis_id=analysis_id,
                user_id=user_id,
                normalized=normalized,
                source_info=source_info,
                source=source,
                kind=kind,
                title=_title_from_url(normalized),
                description=None,
                duration=None,
                published=None,
                candidates=[candidate],
                thumbnail_source=fetched.url if kind == "image" else None,
                playback=PlaybackInfo(mode="file", url=fetched.url),
                drm=False,
                warnings=warnings,
            )

    text = fetched.content[:250_000].decode("utf-8", "ignore")
    lowered = text.lstrip().lower()

    is_manifest = (
        fetched.content_type in {"application/vnd.apple.mpegurl", "application/dash+xml"}
        or lowered.startswith("#extm3u")
        or suffix in {".m3u8", ".mpd"}
    )
    if is_manifest:
        drm = metadata_service.detect_drm(text)
        if drm:
            warnings.append(
                "Konten dilindungi DRM. Unduhan tidak tersedia; pemutaran hanya lewat embed resmi."
            )
        playback = PlaybackInfo(mode="embed" if drm else "hls", url=None if drm else normalized)
        return await _finish(
            analysis_id=analysis_id,
            user_id=user_id,
            normalized=normalized,
            source_info=source_info,
            source=source,
            kind="stream",
            title=_title_from_url(normalized),
            description=None,
            duration=None,
            published=None,
            candidates=[],
            thumbnail_source=None,
            playback=playback,
            drm=drm,
            warnings=warnings,
        )

    page = metadata_service.extract_page_metadata(text, fetched.url)
    title = page.title or _title_from_url(normalized)
    description = page.description

    video_urls = _dedupe(page.video_candidates, 5)
    image_urls = _dedupe(
        page.thumbnail_candidates + page.image_candidates, 21
    )

    if video_urls:
        candidates = [
            Candidate(
                url=url,
                kind="video",
                mime_type=(
                    "application/x-mpegURL"
                    if Path(urlsplit(url).path).suffix.lower() == ".m3u8"
                    else None
                ),
                label="Sumber video",
            )
            for url in video_urls
        ]
        thumbnail = page.thumbnail_candidates[0] if page.thumbnail_candidates else None
        return await _finish(
            analysis_id=analysis_id,
            user_id=user_id,
            normalized=normalized,
            source_info=source_info,
            source=source,
            kind="video",
            title=title,
            description=description,
            duration=page.duration_seconds,
            published=page.published_at,
            candidates=candidates,
            thumbnail_source=thumbnail,
            playback=PlaybackInfo(mode="file", url=video_urls[0]),
            drm=False,
            warnings=warnings,
        )

    if image_urls:
        candidates = [
            Candidate(url=url, kind="image", label="Gambar")
            for url in image_urls[:20]
        ]
        return await _finish(
            analysis_id=analysis_id,
            user_id=user_id,
            normalized=normalized,
            source_info=source_info,
            source=source,
            kind="image",
            title=title,
            description=description,
            duration=None,
            published=page.published_at,
            candidates=candidates,
            thumbnail_source=image_urls[0],
            playback=PlaybackInfo(mode="file", url=image_urls[0]),
            drm=False,
            warnings=warnings,
        )

    warnings.append("Tidak ada media yang bisa diunduh dari halaman ini.")
    return await _finish(
        analysis_id=analysis_id,
        user_id=user_id,
        normalized=normalized,
        source_info=source_info,
        source=source,
        kind="page",
        title=title,
        description=description,
        duration=None,
        published=page.published_at,
        candidates=[],
        thumbnail_source=page.thumbnail_candidates[0]
        if page.thumbnail_candidates
        else None,
        playback=PlaybackInfo(mode="none", url=None),
        drm=False,
        warnings=warnings,
    )
