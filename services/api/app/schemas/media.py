from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    host: str | None = None
    display_name: str | None = None


class ProgressRef(BaseModel):
    position_seconds: int = 0
    completed: bool = False


class MediaOut(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    kind: Literal["video", "image", "stream", "page"]
    category: str | None = None
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    embed_url: str | None = None
    thumbnail_url: str | None = None
    stream_url: str | None = None
    source: SourceRef
    is_favorite: bool = False
    progress: ProgressRef = Field(default_factory=ProgressRef)
    created_at: datetime


class MediaListOut(BaseModel):
    items: list[MediaOut]
    total: int
    limit: int
    offset: int


class MediaPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=40)


class DownloadCreate(BaseModel):
    url: str = Field(min_length=3, max_length=2048)
    analysis_id: str | None = None
    title: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=40)


class DownloadOut(BaseModel):
    id: UUID
    state: str
    url: str
    bytes_total: int | None = None
    bytes_done: int = 0
    progress: int = 0
    error_code: str | None = None
    error_message: str | None = None
    media_id: UUID | None = None
    created_at: datetime
    finished_at: datetime | None = None


class WatchHistoryIn(BaseModel):
    media_id: UUID
    position_seconds: int = Field(ge=0)
    duration_seconds: int | None = Field(default=None, ge=1)


class WatchHistoryOut(BaseModel):
    media_id: UUID
    position_seconds: int
    duration_seconds: int | None
    completed: bool
    play_count: int
    last_watched_at: datetime


class CollectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class CollectionOut(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str | None = None
    item_count: int = 0
    created_at: datetime


class CollectionDetail(CollectionOut):
    items: list[MediaOut] = Field(default_factory=list)


class CollectionItemIn(BaseModel):
    media_id: UUID


class RecommendationOut(BaseModel):
    media_id: UUID
    title: str
    category: str | None
    thumbnail_url: str | None
    reason: str
    reason_label: str
    score: float
