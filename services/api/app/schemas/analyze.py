from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=3, max_length=2048)
    content_hint: Literal["auto", "video", "image", "stream"] = "auto"


class SourceInfo(BaseModel):
    host: str
    display_name: str
    policy: str


class Candidate(BaseModel):
    url: str
    kind: Literal["video", "image"]
    mime_type: str | None = None
    bytes: int | None = None
    width: int | None = None
    height: int | None = None
    label: str | None = None


class DownloadPolicy(BaseModel):
    allowed: bool
    reason: str
    max_bytes: int


class PlaybackInfo(BaseModel):
    mode: Literal["file", "embed", "hls", "none"]
    url: str | None = None


class AnalyzeResponse(BaseModel):
    analysis_id: str
    input_url: str
    canonical_url: str
    kind: Literal["video", "image", "stream", "page"]
    source: SourceInfo
    title: str
    description: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    published_at: str | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    download: DownloadPolicy
    playback: PlaybackInfo
    warnings: list[str] = Field(default_factory=list)
