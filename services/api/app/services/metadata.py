import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

ISO_DURATION = re.compile(
    r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$", re.IGNORECASE
)
YOUTUBE_PATTERN = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})"
)
VIMEO_PATTERN = re.compile(r"vimeo\.com/(?:video/)?(\d+)")


@dataclass
class PageMetadata:
    title: str | None = None
    description: str | None = None
    site_name: str | None = None
    duration_seconds: int | None = None
    published_at: str | None = None
    thumbnail_candidates: list[str] = field(default_factory=list)
    video_candidates: list[str] = field(default_factory=list)
    image_candidates: list[str] = field(default_factory=list)
    embed_url: str | None = None


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.json_ld: list[str] = []
        self.videos: list[str] = []
        self.images: list[str] = []
        self._in_title = False
        self._script_is_jsonld = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if key and content and key not in self.meta:
                self.meta[key] = content
        elif tag == "title":
            self._in_title = True
        elif tag == "script":
            if values.get("type", "").lower() == "application/ld+json":
                self._script_is_jsonld = True
                self._script_parts = []
        elif tag == "video" and values.get("src"):
            self.videos.append(values["src"])
        elif tag == "source" and values.get("src"):
            self.videos.append(values["src"])
        elif tag == "img" and values.get("src"):
            self.images.append(values["src"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._script_is_jsonld:
            self.json_ld.append("".join(self._script_parts))
            self._script_is_jsonld = False
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._script_is_jsonld:
            self._script_parts.append(data)


def parse_duration(value: str | None) -> int | None:
    if not value:
        return None
    if value.isdigit():
        return int(value)
    match = ISO_DURATION.match(value.strip())
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(float(seconds or 0))


def _flatten_json_ld(payload: object) -> list[dict]:
    if isinstance(payload, list):
        result: list[dict] = []
        for item in payload:
            result.extend(_flatten_json_ld(item))
        return result
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return _flatten_json_ld(graph)
        return [payload]
    return []


def extract_page_metadata(html: str, base_url: str) -> PageMetadata:
    parser = _MetadataParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    meta = parser.meta
    metadata = PageMetadata()
    metadata.title = (
        meta.get("og:title")
        or meta.get("twitter:title")
        or "".join(parser.title_parts).strip()
        or None
    )
    metadata.description = (
        meta.get("og:description")
        or meta.get("twitter:description")
        or meta.get("description")
        or None
    )
    metadata.site_name = meta.get("og:site_name")
    metadata.duration_seconds = parse_duration(
        meta.get("og:video:duration") or meta.get("video:duration")
    )
    metadata.published_at = (
        meta.get("article:published_time")
        or meta.get("og:video:release_date")
        or meta.get("date")
    )

    for key in ("og:image", "og:image:url", "og:image:secure_url", "twitter:image"):
        value = meta.get(key)
        if value:
            metadata.thumbnail_candidates.append(urljoin(base_url, value))

    for key in ("og:video", "og:video:url", "og:video:secure_url", "twitter:player:stream"):
        value = meta.get(key)
        if value:
            metadata.video_candidates.append(urljoin(base_url, value))

    for raw in parser.videos:
        metadata.video_candidates.append(urljoin(base_url, raw))

    for raw in parser.images:
        if raw.startswith("data:"):
            continue
        metadata.image_candidates.append(urljoin(base_url, raw))

    for raw in parser.json_ld:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for item in _flatten_json_ld(payload):
            item_type = str(item.get("@type", ""))
            if item.get("thumbnailUrl"):
                thumb = item["thumbnailUrl"]
                if isinstance(thumb, list):
                    metadata.thumbnail_candidates.extend(str(value) for value in thumb[:3])
                else:
                    metadata.thumbnail_candidates.append(str(thumb))
            if item_type in {"VideoObject", "Movie", "Clip"}:
                if item.get("contentUrl"):
                    metadata.video_candidates.append(str(item["contentUrl"]))
                if item.get("embedUrl"):
                    metadata.embed_url = str(item["embedUrl"])
                if item.get("name") and not metadata.title:
                    metadata.title = str(item["name"])
                if item.get("description") and not metadata.description:
                    metadata.description = str(item["description"])
                if item.get("duration") and metadata.duration_seconds is None:
                    metadata.duration_seconds = parse_duration(str(item["duration"]))
                if item.get("uploadDate") and not metadata.published_at:
                    metadata.published_at = str(item["uploadDate"])
            if item_type in {"ImageObject", "ImageGallery"} and item.get("contentUrl"):
                metadata.image_candidates.append(str(item["contentUrl"]))

    return metadata


def youtube_id(url: str) -> str | None:
    match = YOUTUBE_PATTERN.search(url)
    return match.group(1) if match else None


def vimeo_id(url: str) -> str | None:
    match = VIMEO_PATTERN.search(url)
    return match.group(1) if match else None


def embed_url_for(url: str) -> str | None:
    yt = youtube_id(url)
    if yt:
        return f"https://www.youtube-nocookie.com/embed/{yt}"
    vimeo = vimeo_id(url)
    if vimeo:
        return f"https://player.vimeo.com/video/{vimeo}"
    return None


def detect_drm(text: str) -> bool:
    lowered = text[:200_000].lower()
    if "#ext-x-key" in lowered and ("sample-aes" in lowered or "aes-128" in lowered):
        return True
    if "#ext-x-session-key" in lowered:
        return True
    if "<contentprotection" in lowered:
        return True
    return "widevine" in lowered or "playready" in lowered
