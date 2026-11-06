"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATEMENTS = [
    "create extension if not exists pg_trgm",
    "create type media_kind as enum ('video', 'image', 'stream', 'page')",
    "create type media_status as enum ('processing', 'ready', 'failed')",
    (
        "create type job_state as enum ('queued', 'resolving', 'downloading', "
        "'processing', 'completed', 'failed', 'cancelled', 'blocked')"
    ),
    (
        "create type source_policy as enum ('download_allowed', 'embed_only', "
        "'pending_review', 'blocked')"
    ),
    (
        "create type file_role as enum ('original', 'thumbnail', 'poster', "
        "'sprite', 'subtitle')"
    ),
    """
    create table users (
      id            uuid primary key default gen_random_uuid(),
      email         text not null,
      password_hash text not null,
      display_name  text not null,
      is_admin      boolean not null default false,
      created_at    timestamptz not null default now(),
      last_login_at timestamptz,
      deleted_at    timestamptz
    )
    """,
    "create unique index users_email_lower_uniq on users (lower(email)) where deleted_at is null",
    """
    create table sessions (
      id         uuid primary key default gen_random_uuid(),
      user_id    uuid not null references users(id) on delete cascade,
      token_hash char(64) not null unique,
      user_agent text,
      ip         inet,
      created_at timestamptz not null default now(),
      expires_at timestamptz not null,
      revoked_at timestamptz
    )
    """,
    "create index sessions_user_idx on sessions (user_id)",
    """
    create table sources (
      id                 uuid primary key default gen_random_uuid(),
      host               text not null unique,
      display_name       text not null,
      policy             source_policy not null default 'pending_review',
      include_subdomains boolean not null default true,
      max_file_bytes     bigint not null default 2147483648,
      notes              text,
      reviewed_at        timestamptz,
      created_at         timestamptz not null default now()
    )
    """,
    """
    create table media_items (
      id                  uuid primary key default gen_random_uuid(),
      user_id             uuid not null references users(id) on delete cascade,
      source_id           uuid references sources(id) on delete set null,
      source_url          text not null,
      canonical_url       text not null,
      kind                media_kind not null,
      embed_url           text,
      title               text not null,
      description         text,
      category            text,
      category_confidence real,
      category_locked     boolean not null default false,
      duration_seconds    integer,
      width               integer,
      height              integer,
      language            text,
      published_at        timestamptz,
      status              media_status not null default 'processing',
      created_at          timestamptz not null default now(),
      updated_at          timestamptz not null default now(),
      deleted_at          timestamptz
    )
    """,
    (
        "create index media_items_user_created_idx on media_items (user_id, created_at desc) "
        "where deleted_at is null"
    ),
    (
        "create index media_items_user_kind_idx on media_items (user_id, kind) "
        "where deleted_at is null"
    ),
    (
        "create index media_items_user_category_idx on media_items (user_id, category) "
        "where deleted_at is null"
    ),
    "create index media_items_title_trgm_idx on media_items using gin (title gin_trgm_ops)",
    (
        "create unique index media_items_user_url_uniq on media_items (user_id, canonical_url) "
        "where deleted_at is null"
    ),
    """
    create table media_files (
      id              uuid primary key default gen_random_uuid(),
      media_item_id   uuid not null references media_items(id) on delete cascade,
      role            file_role not null,
      language        text not null default 'und',
      storage_driver  text not null default 'local',
      storage_key     text not null,
      mime_type       text not null,
      bytes           bigint not null,
      checksum_sha256 char(64),
      width           integer,
      height          integer,
      created_at      timestamptz not null default now(),
      unique (media_item_id, role, language),
      unique (storage_driver, storage_key)
    )
    """,
    "create index media_files_checksum_idx on media_files (checksum_sha256)",
    "create index media_files_item_idx on media_files (media_item_id)",
    """
    create table download_jobs (
      id              uuid primary key default gen_random_uuid(),
      user_id         uuid not null references users(id) on delete cascade,
      media_item_id   uuid references media_items(id) on delete set null,
      source_id       uuid references sources(id) on delete set null,
      url             text not null,
      url_hash        char(64) not null,
      state           job_state not null default 'queued',
      bytes_total     bigint,
      bytes_done      bigint not null default 0,
      attempts        integer not null default 0,
      error_code      text,
      error_message   text,
      idempotency_key text,
      created_at      timestamptz not null default now(),
      started_at      timestamptz,
      finished_at     timestamptz
    )
    """,
    (
        "create unique index download_jobs_idem_uniq on download_jobs "
        "(user_id, idempotency_key) where idempotency_key is not null"
    ),
    (
        "create unique index download_jobs_active_uniq on download_jobs (user_id, url_hash) "
        "where state in ('queued', 'resolving', 'downloading', 'processing')"
    ),
    "create index download_jobs_user_state_idx on download_jobs (user_id, state)",
    """
    create table collections (
      id             uuid primary key default gen_random_uuid(),
      user_id        uuid not null references users(id) on delete cascade,
      title          text not null,
      slug           text not null,
      description    text,
      cover_media_id uuid references media_items(id) on delete set null,
      smart_rules    jsonb,
      created_at     timestamptz not null default now(),
      unique (user_id, slug)
    )
    """,
    """
    create table collection_items (
      collection_id uuid not null references collections(id) on delete cascade,
      media_item_id uuid not null references media_items(id) on delete cascade,
      position      integer not null default 0,
      added_at      timestamptz not null default now(),
      primary key (collection_id, media_item_id)
    )
    """,
    """
    create table watch_history (
      user_id          uuid not null references users(id) on delete cascade,
      media_item_id    uuid not null references media_items(id) on delete cascade,
      position_seconds integer not null default 0,
      duration_seconds integer,
      completed        boolean not null default false,
      play_count       integer not null default 1,
      last_watched_at  timestamptz not null default now(),
      primary key (user_id, media_item_id)
    )
    """,
    "create index watch_history_recent_idx on watch_history (user_id, last_watched_at desc)",
    """
    create table favorites (
      user_id       uuid not null references users(id) on delete cascade,
      media_item_id uuid not null references media_items(id) on delete cascade,
      created_at    timestamptz not null default now(),
      primary key (user_id, media_item_id)
    )
    """,
    """
    create table tags (
      id    uuid primary key default gen_random_uuid(),
      slug  text not null unique,
      label text not null,
      kind  text not null default 'topic'
    )
    """,
    """
    create table media_item_tags (
      media_item_id uuid not null references media_items(id) on delete cascade,
      tag_id        uuid not null references tags(id) on delete cascade,
      confidence    real not null default 1.0,
      source        text not null default 'auto',
      primary key (media_item_id, tag_id)
    )
    """,
    """
    create table recommendations (
      id            uuid primary key default gen_random_uuid(),
      user_id       uuid not null references users(id) on delete cascade,
      media_item_id uuid not null references media_items(id) on delete cascade,
      surface       text not null default 'home',
      score         real not null,
      reason        text not null,
      algorithm     text not null default 'content_v1',
      generated_at  timestamptz not null default now(),
      expires_at    timestamptz not null,
      unique (user_id, media_item_id, surface)
    )
    """,
    (
        "create index recommendations_user_surface_idx on recommendations "
        "(user_id, surface, score desc)"
    ),
    """
    create table audit_log (
      id           bigserial primary key,
      user_id      uuid references users(id) on delete set null,
      action       text not null,
      subject_type text,
      subject_id   text,
      metadata     jsonb not null default '{}'::jsonb,
      ip           inet,
      created_at   timestamptz not null default now()
    )
    """,
    "create index audit_log_user_time_idx on audit_log (user_id, created_at desc)",
]

DOWNGRADE = [
    "drop table if exists audit_log",
    "drop table if exists recommendations",
    "drop table if exists media_item_tags",
    "drop table if exists tags",
    "drop table if exists favorites",
    "drop table if exists watch_history",
    "drop table if exists collection_items",
    "drop table if exists collections",
    "drop table if exists download_jobs",
    "drop table if exists media_files",
    "drop table if exists media_items",
    "drop table if exists sources",
    "drop table if exists sessions",
    "drop table if exists users",
    "drop type if exists file_role",
    "drop type if exists source_policy",
    "drop type if exists job_state",
    "drop type if exists media_status",
    "drop type if exists media_kind",
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
