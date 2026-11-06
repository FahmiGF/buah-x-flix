# BLUEPRINT IMPLEMENTASI — UNIVERSAL VIDEO HUB

**Dokumen:** Blueprint Teknis & Produk v1.0
**Tanggal:** 6 November 2026
**Status:** Siap eksekusi — keputusan arsitektur sudah dikunci, sisa pekerjaan adalah implementasi bertahap.
**Cakupan:** Application A (Peach Finder) + Application B (My Netflix) + satu backend bersama.

> **Find anything. Save what you can. Watch everything in one place.**

---

## DAFTAR ISI

0. [Cara Memakai Blueprint Ini](#0-cara-memakai-blueprint-ini)
1. [Keputusan Produk yang Dikunci](#1-keputusan-produk-yang-dikunci)
2. [Definisi MVP dan Non-Goals](#2-definisi-mvp-dan-non-goals)
3. [Arsitektur Sistem](#3-arsitektur-sistem)
4. [Struktur Repositori](#4-struktur-repositori)
5. [Model Data](#5-model-data)
6. [Kontrak API](#6-kontrak-api)
7. [URL Analyzer](#7-url-analyzer)
8. [Download Engine](#8-download-engine)
9. [Media Ingestion dan Processing](#9-media-ingestion-dan-processing)
10. [Recommendation Engine](#10-recommendation-engine)
11. [Blueprint UI Aplikasi 1: Peach Finder](#11-blueprint-ui-aplikasi-1-peach-finder)
12. [Blueprint UI Aplikasi 2: My Netflix](#12-blueprint-ui-aplikasi-2-my-netflix)
13. [Keamanan, Legal, dan Privasi](#13-keamanan-legal-dan-privasi)
14. [Infrastruktur dan Deployment](#14-infrastruktur-dan-deployment)
15. [Roadmap dan Task Breakdown](#15-roadmap-dan-task-breakdown)
16. [Strategi Pengujian](#16-strategi-pengujian)
17. [Risiko dan Mitigasi](#17-risiko-dan-mitigasi)
18. [Definition of Done](#18-definition-of-done)
- [Lampiran A: Registry Sumber Awal](#lampiran-a-registry-sumber-awal)
- [Lampiran B: Variabel Environment](#lampiran-b-variabel-environment)
- [Lampiran C: Kode Error](#lampiran-c-kode-error)

---

## 0. Cara Memakai Blueprint Ini

Blueprint ini adalah **kontrak eksekusi**, bukan proposal. Setiap keputusan di §1 sudah dipilih; setiap tabel, endpoint, dan state machine di bawah adalah target implementasi. Kalau saat coding ditemukan alasan kuat untuk menyimpang, ubah dokumen ini di PR yang sama agar tidak ada dua sumber kebenaran.

Penanda prioritas yang dipakai:

| Penanda | Arti |
|---|---|
| **[MVP]** | Wajib ada di versi pertama. Tanpa ini, demo dua aplikasi terhubung dianggap gagal. |
| **[P1]** | Penting, dikerjakan setelah MVP stabil. |
| **[NANTI]** | Direncanakan, tetapi sengaja ditunda (desktop, mobile, embedding, collaborative filtering). |

Aturan kerja:

1. Kerjakan fase secara berurutan (§15). Jangan mulai Phase 3 sebelum acceptance criteria Phase 2 lulus.
2. Setiap endpoint baru wajib punya test kepemilikan (user A tidak boleh membaca resource user B).
3. Setiap perubahan skema wajib lewat migrasi Alembic; tidak ada `create_all()` di runtime.
4. Dokumen ini berbahasa Indonesia; identifier kode, nama tabel, dan nama endpoint berbahasa Inggris.

---

## 1. Keputusan Produk yang Dikunci

Bagian §14 masterplan meminta empat keputusan. Berikut jawabannya, beserta konsekuensi teknisnya.

| Aspek | Keputusan | Alasan | Konsekuensi |
|---|---|---|---|
| **Platform** | **Web app dulu** (dua frontend Next.js), desktop Tauri di Phase 6 | Web paling cepat memvalidasi alur analyze → download → library; Tauri butuh sidecar API + packaging yang belum perlu di MVP | Backend harus stateless terhadap filesystem lokal agar nanti bisa dibungkus sidecar desktop |
| **Penyimpanan** | **Local-first** dengan `StorageDriver`; adapter S3/MinIO disiapkan dan diaktifkan lewat env | File video besar; biaya cloud mahal untuk eksperimen; hybrid tetap mungkin tanpa refactor | Semua akses file lewat abstraksi storage, tidak ada `open()` langsung di route handler |
| **Sumber** | URL publik (file langsung + halaman dengan metadata) + upload file lokal + embed resmi; **tanpa DRM** | Menjaga produk legal dan menghindari bypass teknis | Download hanya untuk host yang lolos registry (§13); domain tak dikenal = `pending_review` |
| **UI** | **Dark premium** untuk keduanya; App 1 aksen peach, App 2 aksen crimson sinematik | Masterplan merekomendasikan dark premium; dua karakter tetap terasa berbeda | Dua design token set terpisah, satu component library bersama |

Keputusan tambahan yang ikut dikunci:

| Topik | Keputusan |
|---|---|
| Autentikasi | Email + password (Argon2id), session cookie httpOnly. OAuth **[P1]**. |
| Model pengguna | Satu akun = satu perpustakaan pribadi. Berbagi/keluarga **[NANTI]**. |
| Bahasa UI | Bahasa Indonesia; semua string di `lib/i18n.ts` agar bisa di-i18n-kan. |
| Nama produk | "Universal Video Hub" sebagai ekosistem; "Peach Finder" dan "My Netflix" sebagai nama aplikasi kerja. Nama komersial final masih terbuka, tetapi **tidak boleh memakai logo/merek Netflix**. |
| Rekomendasi | Content-based + tag/recency/completion sejak Phase 5. Collaborative filtering dan embedding baru setelah ada data nyata. |
| Upload file lokal | Termasuk MVP karena menjadi jalur demo yang 100% legal dan tidak bergantung jaringan. |

### 1.1 Prinsip yang tidak boleh dilanggar

1. **Legal-first.** Tidak ada circumvention DRM, tidak ada akses ke konten berbayar/login, tidak ada scraping platform yang melarangnya.
2. **SSRF-safe.** Semua fetch keluar lewat satu modul yang memvalidasi IP, redirect, ukuran, dan waktu.
3. **Ownership-safe.** Setiap query media/file/job difilter `user_id`; tidak ada IDOR.
4. **Local-first.** Aplikasi tetap bisa menyajikan file yang sudah diunduh tanpa internet.
5. **Two apps, one truth.** Kedua frontend membaca database dan API yang sama; tidak ada penyimpanan metadata ganda.

---

## 2. Definisi MVP dan Non-Goals

### 2.1 Checklist MVP (10 item dari masterplan)

| # | Item | Fase | Bukti bahwa selesai |
|---|---|---|---|
| 1 | Input URL dan analisis metadata | 2 | `POST /analyze` mengembalikan judul, tipe, thumbnail, kandidat file |
| 2 | Preview video dan gambar | 2 | Kartu hasil menampilkan thumbnail ter-cache dan player preview untuk file langsung |
| 3 | Download file HTTP yang diizinkan | 3 | Job berjalan untuk host `download_allowed`, file tersimpan dengan checksum |
| 4 | Download manager dengan progress | 3 | Halaman antrean menampilkan progress real-time (SSE) |
| 5 | Penyimpanan lokal | 1–3 | File ada di `media-library/u_<id>/...`, metadata di Postgres |
| 6 | Sinkronisasi ke aplikasi kedua | 3 | Setelah job `completed`, item muncul di My Netflix tanpa langkah manual |
| 7 | Netflix-style homepage | 4 | Hero + minimal 6 baris konten dari data nyata |
| 8 | Video player lokal | 4 | Player HTML5 dengan Range request, seek, fullscreen |
| 9 | Search dan kategori | 4 | Pencarian judul/deskripsi + filter tipe/kategori |
| 10 | Favorites dan collections | 4 | Favorit per akun; koleksi bisa dibuat dan diisi |

### 2.2 Non-goals MVP

- Bukan pengunduh YouTube/TikTok/Instagram/Netflix. Platform tersebut hanya `embed_only` lewat oEmbed resmi.
- Tidak ada konversi HLS/DASH menjadi file pada MVP. Manifest non-DRM ditandai `stream` dan diputar via embed/player HLS bila sumber mengizinkan; pengunduhan segmen ditunda dan hanya boleh untuk host yang secara eksplisit mengizinkan.
- Tidak ada DRM, paywall, autentikasi platform, torrent, atau IPTV.
- Tidak ada mobile app, desktop app, multi-user sharing, komentar sosial, atau transcode ladder.
- Tidak ada AI generatif. "AI" pada MVP berarti klasifikasi berbasis aturan + skor rekomendasi yang dapat dijelaskan.

---

## 3. Arsitektur Sistem

### 3.1 Diagram komponen

```
+------------------------------+          +------------------------------+
|  App A: Peach Finder         |          |  App B: My Netflix           |
|  Next.js 15 (App Router)     |          |  Next.js 15 (App Router)     |
|  :3000                       |          |  :3001                       |
+--------------+---------------+          +--------------+---------------+
               |  /api/* rewrite (cookie first-party)   |
               +------------------+---------------------+
                                  v
                    +-----------------------------+
                    |  FastAPI :8000              |
                    |  REST + SSE + Range stream  |
                    |  Auth, ownership, policy    |
                    +----+-------------+----------+
                         |             |
          +--------------+             +------------------+
          v                                               v
  +----------------+                          +----------------------+
  | PostgreSQL 16  |                          | Redis 7              |
  | metadata, jobs |                          | cache, broker, locks |
  +----------------+                          +----------+-----------+
                                                         |
                                +------------------------+-----------------------+
                                v                        v                       v
                        +---------------+        +---------------+       +------------------+
                        | Celery worker |        | Celery worker |       | Celery beat      |
                        | queue:        |        | queue:        |       | nightly reco,    |
                        | download      |        | process       |       | stale-job sweep  |
                        +-------+-------+        +-------+-------+       +------------------+
                                |                        |
                                +-----------+------------+
                                            v
                              +-----------------------------+
                              | StorageDriver               |
                              | local ./media-library       |
                              | atau S3/MinIO               |
                              +-----------------------------+
```

Prinsip pemisahan:

- **API tidak pernah mengunduh file besar.** API hanya memvalidasi, membuat job, dan membaca metadata. Semua transfer berat terjadi di worker.
- **Analyzer adalah modul, bukan service terpisah pada MVP.** Ia dipanggil API secara in-process; batas modulnya tegas agar nanti bisa dipisah.
- **Worker dan API berbagi kode domain** lewat `services/api/app/` (satu image Docker, dua entrypoint).
- **Frontend tidak menyimpan token di localStorage.** Auth memakai cookie httpOnly yang diproksikan oleh rewrite Next.js, sehingga cookie tetap first-party di tiap app.

### 3.2 Alur utama: URL → perpustakaan

```
User (Peach Finder)
  |  tempel URL
  v
POST /api/v1/analyze
  |-- normalisasi URL + validasi skema
  |-- resolusi DNS + blokir IP privat (SSRF)
  |-- fetch terbatas (redirect divalidasi ulang)
  |-- deteksi tipe: video | image | stream | page
  |-- ekstraksi metadata (OG, JSON-LD, oEmbed, header file)
  |-- cek registry sumber + DRM
  v
AnalyzeResult (disimpan di Redis 30 menit, bukan DB)
  |  user menekan "Unduh"
  v
POST /api/v1/downloads  (Idempotency-Key)
  |-- validasi ulang URL + policy (jangan percaya hasil analyze)
  |-- buat download_jobs state=queued
  v
Celery queue download
  |-- resolving -> downloading (Range resume, retry)
  |-- file .part + sha256 -> atomic rename
  |-- download_jobs state=processing
  v
Celery queue process
  |-- ffprobe, thumbnail, validasi, kategori otomatis, dedupe
  |-- media_items state=ready + media_files
  v
My Netflix (polling/refresh) menampilkan item baru
```

### 3.3 Stack final

| Layer | Pilihan | Versi minimum | Catatan |
|---|---|---|---|
| Frontend | Next.js + React + TypeScript | Next 15, React 19 | Dua app, satu `packages/ui` |
| Styling | Tailwind CSS + komponen milik sendiri | Tailwind 4 | shadcn/ui boleh diadopsi, tetapi komponen kustom lebih penting untuk karakter visual |
| Backend | FastAPI + Pydantic v2 | Python 3.12, FastAPI 0.115 | Async untuk API, sync untuk worker |
| ORM/Migrasi | SQLAlchemy 2 + Alembic | — | Async session di API |
| Database | PostgreSQL | 16 | `pg_trgm` untuk pencarian judul |
| Queue | Celery + Redis | Celery 5.4, Redis 7 | Tiga queue terpisah |
| Media | FFmpeg/ffprobe, Pillow | FFmpeg 7 | Dipanggil lewat subprocess dengan timeout |
| Storage | Filesystem + adapter S3 | — | `boto3` hanya saat driver s3 aktif |
| Auth | Sendiri: Argon2id + session | argon2-cffi | Alasan: dua frontend, satu cookie domain |
| Package manager | pnpm (Node), uv (Python) | pnpm 9, uv 0.5 | Lockfile wajib di-commit |
| Desktop | Tauri | 2.x | Phase 6, tidak masuk MVP |

---

## 4. Struktur Repositori

```
universal-video-hub/
├── apps/
│   ├── video-finder/                 # App A — Peach Finder
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # dashboard analyze
│   │   │   ├── history/page.tsx
│   │   │   ├── downloads/[id]/page.tsx
│   │   │   ├── settings/page.tsx
│   │   │   ├── login/page.tsx
│   │   │   └── api/[...path]/route.ts  # optional proxy; default pakai rewrites
│   │   ├── components/
│   │   │   ├── analyze-form.tsx
│   │   │   ├── result-card.tsx
│   │   │   ├── download-queue.tsx
│   │   │   └── source-badge.tsx
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   ├── i18n.ts
│   │   │   └── format.ts
│   │   ├── next.config.ts            # rewrites /api -> API_URL
│   │   └── app/globals.css
│   └── my-netflix/                   # App B — My Netflix
│       ├── app/
│       │   ├── page.tsx              # home
│       │   ├── browse/[kind]/page.tsx
│       │   ├── search/page.tsx
│       │   ├── title/[id]/page.tsx
│       │   ├── watch/[id]/page.tsx
│       │   ├── collections/page.tsx
│       │   ├── collections/[id]/page.tsx
│       │   ├── favorites/page.tsx
│       │   ├── downloads/page.tsx
│       │   └── login/page.tsx
│       ├── components/
│       │   ├── hero.tsx
│       │   ├── media-row.tsx
│       │   ├── media-card.tsx
│       │   ├── player.tsx
│       │   └── collection-picker.tsx
│       ├── lib/
│       └── next.config.ts
├── services/
│   └── api/
│       ├── app/
│       │   ├── main.py               # create_app(), router mounting
│       │   ├── config.py             # Settings (pydantic-settings)
│       │   ├── deps.py               # current_user, db session
│       │   ├── models/               # SQLAlchemy: user, media, job, ...
│       │   ├── schemas/              # Pydantic request/response
│       │   ├── routers/
│       │   │   ├── auth.py
│       │   │   ├── analyze.py
│       │   │   ├── media.py
│       │   │   ├── downloads.py
│       │   │   ├── collections.py
│       │   │   ├── library.py        # watch history, favorites
│       │   │   └── recommendations.py
│       │   ├── services/
│       │   │   ├── analyzer/
│       │   │   │   ├── fetch.py      # safe_fetch + SSRF guard
│       │   │   │   ├── detect.py
│       │   │   │   ├── metadata.py
│       │   │   │   ├── oembed.py
│       │   │   │   └── policy.py
│       │   │   ├── download/
│       │   │   │   ├── engine.py
│       │   │   │   └── naming.py
│       │   │   ├── ingest.py
│       │   │   ├── storage.py        # StorageDriver protocol + local/s3
│       │   │   ├── recommendations.py
│       │   │   └── security.py       # signed URLs, origin check
│       │   ├── worker.py             # Celery app + tasks
│       │   └── cli.py                # approve-source, seed-demo
│       ├── alembic/versions/
│       ├── tests/
│       │   ├── unit/
│       │   ├── integration/
│       │   └── security/
│       ├── pyproject.toml
│       └── Dockerfile
├── packages/
│   ├── ui/                           # komponen bersama + tokens
│   └── shared-types/                 # hasil generate OpenAPI (typescript)
├── infrastructure/
│   ├── docker-compose.yml
│   └── caddy/Caddyfile               # reverse proxy produksi
├── media-library/                    # runtime, git-ignored
├── scripts/
│   ├── dev.sh
│   └── demo-seed.sh
├── BLUEPRINT.md
├── README.md
└── .env.example
```

Aturan batas modul:

- `apps/*` tidak mengimpor kode Python; komunikasi hanya HTTP.
- `services/api/app/models` tidak mengimpor `services/*` lain kecuali `storage` dan `config`.
- `packages/ui` tidak tahu API; semua data lewat props.
- File media dan `media-library/` tidak pernah masuk git.

---

## 5. Model Data

### 5.1 ERD ringkas

```
users 1---* sessions
users 1---* media_items *---1 sources
media_items 1---* media_files
media_items 1---* download_jobs (nullable, job bisa belum jadi item)
users 1---* collections 1---* collection_items *---1 media_items
users 1---* watch_history *---1 media_items
users 1---* favorites *---1 media_items
media_items *---* tags (lewat media_item_tags)
users 1---* recommendations *---1 media_items
users 1---* audit_log
```

Catatan pemetaan terhadap masterplan:

| Masterplan | Implementasi | Alasan |
|---|---|---|
| `permissions` | kolom `policy` pada `sources` + `audit_log` | Hak unduh melekat pada sumber, bukan pada user; audit mencatat keputusan |
| `media_tags` | `tags` + `media_item_tags` | Menghindari duplikasi string tag dan memudahkan agregasi rekomendasi |
| `recommendations` | tetap, ditambah `surface`, `score`, `reason` | Penjelasan rekomendasi adalah fitur produk, bukan sekadar skor |

### 5.2 DDL PostgreSQL

```sql
create extension if not exists pg_trgm;

create type media_kind   as enum ('video', 'image', 'stream', 'page');
create type media_status as enum ('processing', 'ready', 'failed');
create type job_state    as enum ('queued', 'resolving', 'downloading',
                                  'processing', 'completed', 'failed',
                                  'cancelled', 'blocked');
create type source_policy as enum ('download_allowed', 'embed_only',
                                   'pending_review', 'blocked');
create type file_role    as enum ('original', 'thumbnail', 'poster', 'sprite', 'subtitle');

create table users (
  id            uuid primary key default gen_random_uuid(),
  email         text not null,
  password_hash text not null,
  display_name  text not null,
  is_admin      boolean not null default false,
  created_at    timestamptz not null default now(),
  last_login_at timestamptz,
  deleted_at    timestamptz
);
create unique index users_email_lower_uniq
  on users (lower(email)) where deleted_at is null;

create table sessions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users(id) on delete cascade,
  token_hash char(64) not null unique,
  user_agent text,
  ip         inet,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  revoked_at timestamptz
);
create index sessions_user_idx on sessions (user_id);

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
);

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
);
create index media_items_user_created_idx
  on media_items (user_id, created_at desc) where deleted_at is null;
create index media_items_user_kind_idx
  on media_items (user_id, kind) where deleted_at is null;
create index media_items_user_category_idx
  on media_items (user_id, category) where deleted_at is null;
create index media_items_title_trgm_idx
  on media_items using gin (title gin_trgm_ops);
create unique index media_items_user_url_uniq
  on media_items (user_id, canonical_url) where deleted_at is null;

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
);
create index media_files_checksum_idx on media_files (checksum_sha256);
create index media_files_item_idx on media_files (media_item_id);

create table download_jobs (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references users(id) on delete cascade,
  media_item_id  uuid references media_items(id) on delete set null,
  source_id      uuid references sources(id) on delete set null,
  url            text not null,
  url_hash       char(64) not null,
  state          job_state not null default 'queued',
  bytes_total    bigint,
  bytes_done     bigint not null default 0,
  attempts       integer not null default 0,
  error_code     text,
  error_message  text,
  idempotency_key text,
  created_at     timestamptz not null default now(),
  started_at     timestamptz,
  finished_at    timestamptz
);
create unique index download_jobs_idem_uniq
  on download_jobs (user_id, idempotency_key) where idempotency_key is not null;
create unique index download_jobs_active_uniq
  on download_jobs (user_id, url_hash)
  where state in ('queued', 'resolving', 'downloading', 'processing');
create index download_jobs_user_state_idx on download_jobs (user_id, state);

create table collections (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(id) on delete cascade,
  title           text not null,
  slug            text not null,
  description     text,
  cover_media_id  uuid references media_items(id) on delete set null,
  smart_rules     jsonb,
  created_at      timestamptz not null default now(),
  unique (user_id, slug)
);

create table collection_items (
  collection_id uuid not null references collections(id) on delete cascade,
  media_item_id uuid not null references media_items(id) on delete cascade,
  position      integer not null default 0,
  added_at      timestamptz not null default now(),
  primary key (collection_id, media_item_id)
);

create table watch_history (
  user_id          uuid not null references users(id) on delete cascade,
  media_item_id    uuid not null references media_items(id) on delete cascade,
  position_seconds integer not null default 0,
  duration_seconds integer,
  completed        boolean not null default false,
  play_count       integer not null default 1,
  last_watched_at  timestamptz not null default now(),
  primary key (user_id, media_item_id)
);
create index watch_history_recent_idx
  on watch_history (user_id, last_watched_at desc);

create table favorites (
  user_id       uuid not null references users(id) on delete cascade,
  media_item_id uuid not null references media_items(id) on delete cascade,
  created_at    timestamptz not null default now(),
  primary key (user_id, media_item_id)
);

create table tags (
  id    uuid primary key default gen_random_uuid(),
  slug  text not null unique,
  label text not null,
  kind  text not null default 'topic'   -- 'category' | 'topic'
);

create table media_item_tags (
  media_item_id uuid not null references media_items(id) on delete cascade,
  tag_id        uuid not null references tags(id) on delete cascade,
  confidence    real not null default 1.0,
  source        text not null default 'auto',   -- 'auto' | 'manual'
  primary key (media_item_id, tag_id)
);

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
);
create index recommendations_user_surface_idx
  on recommendations (user_id, surface, score desc);

create table audit_log (
  id           bigserial primary key,
  user_id      uuid references users(id) on delete set null,
  action       text not null,
  subject_type text,
  subject_id   text,
  metadata     jsonb not null default '{}'::jsonb,
  ip           inet,
  created_at   timestamptz not null default now()
);
create index audit_log_user_time_idx on audit_log (user_id, created_at desc);
```

### 5.3 Aturan integritas yang dijaga di aplikasi

1. `canonical_url` = URL tanpa fragment, query pelacak (`utm_*`, `fbclid`, `gclid`) dibuang, host lowercase. Unik per user agar URL yang sama tidak membuat dua item.
2. Satu media hanya punya satu file `original`. Thumbnail wajib untuk `video`/`image`; `stream` tidak punya file.
3. `download_jobs.state` hanya berubah lewat state machine (§8.1); update progress tidak boleh menimpa state terminal.
4. Menghapus `media_items` = soft delete + hapus file setelah 24 jam (grace period), kecuali user memilih hapus permanen.
5. Semua timestamp UTC (`timestamptz`), format API ISO-8601 dengan `Z`.
6. `storage_key` tidak pernah memakai nama file dari internet mentah-mentah; selalu `<media_id>/<role>.<ext>` (§8.4).

---

## 6. Kontrak API

### 6.1 Konvensi

| Aspek | Aturan |
|---|---|
| Base path | `/api/v1` |
| Format | JSON UTF-8; error memakai envelope `{"error": {"code", "message", "details"}}` |
| ID | UUID v4 |
| Autentikasi | Cookie `uvh_session` (httpOnly, Secure di prod, SameSite=Lax). Bearer token hanya untuk CLI internal |
| CSRF | Validasi header `Origin` untuk semua `POST/PATCH/DELETE`; tolak origin asing |
| Pagination | `?limit=24&cursor=<opaque>` → `{"items": [...], "next_cursor": "..."}` |
| Idempotensi | `POST /downloads` menerima `Idempotency-Key`; key sama mengembalikan job yang sama |
| Request ID | Setiap respons memuat `X-Request-Id`; log worker memuat `job_id` |
| Rate limit | 429 + `Retry-After`; header `X-RateLimit-Remaining` |
| Cache | `ETag` untuk thumbnail; `Cache-Control: private, max-age=300` untuk list |

### 6.2 Daftar endpoint

| Method | Endpoint | Fungsi | Auth |
|---|---|---|---|
| POST | `/auth/register` | Buat akun | publik |
| POST | `/auth/login` | Login, set cookie | publik |
| POST | `/auth/logout` | Revoke session | user |
| GET | `/auth/me` | Profil + kuota | user |
| POST | `/analyze` | Analisis URL | user |
| GET | `/analyze/{analysis_id}/thumbnail` | Proxy thumbnail hasil analisis | user |
| GET | `/sources` | Registry sumber + policy | user |
| POST | `/media/upload` | Upload file lokal | user |
| GET | `/media` | Daftar media + filter | user |
| GET | `/media/{id}` | Detail media | user |
| PATCH | `/media/{id}` | Edit judul/kategori/tag | user |
| DELETE | `/media/{id}` | Hapus media | user |
| GET | `/media/{id}/stream` | Stream file dengan Range | user |
| GET | `/media/{id}/thumbnail` | Thumbnail | user |
| POST | `/downloads` | Buat job unduh | user |
| GET | `/downloads` | Daftar job | user |
| GET | `/downloads/{id}` | Detail job | user |
| DELETE | `/downloads/{id}` | Batalkan job aktif | user |
| POST | `/downloads/{id}/retry` | Retry job gagal | user |
| GET | `/downloads/events` | SSE progress semua job user | user |
| GET | `/collections` | Daftar koleksi | user |
| POST | `/collections` | Buat koleksi | user |
| GET | `/collections/{id}` | Detail + item | user |
| PATCH | `/collections/{id}` | Ubah metadata | user |
| DELETE | `/collections/{id}` | Hapus koleksi (bukan media) | user |
| POST | `/collections/{id}/items` | Tambah media | user |
| DELETE | `/collections/{id}/items/{media_id}` | Keluarkan media | user |
| GET | `/library/continue` | Continue watching | user |
| POST | `/watch-history` | Upsert posisi tontonan | user |
| GET | `/watch-history` | Riwayat | user |
| GET | `/favorites` | Daftar favorit | user |
| PUT | `/favorites/{media_id}` | Tandai favorit (idempoten) | user |
| DELETE | `/favorites/{media_id}` | Hapus favorit | user |
| GET | `/recommendations` | Rekomendasi per surface | user |
| GET | `/health/live` | Liveness | publik |
| GET | `/health/ready` | DB + Redis + storage | publik |

### 6.3 Contoh: `POST /api/v1/analyze`

Request:

```json
{
  "url": "https://commons.wikimedia.org/wiki/File:Big_Buck_Bunny_medium.ogv",
  "content_hint": "auto"
}
```

Response `200`:

```json
{
  "analysis_id": "0f0f0b9e-6d0e-4a5c-9f4b-2f4a3f0b8f11",
  "input_url": "https://commons.wikimedia.org/wiki/File:Big_Buck_Bunny_medium.ogv",
  "canonical_url": "https://commons.wikimedia.org/wiki/File:Big_Buck_Bunny_medium.ogv",
  "kind": "video",
  "source": {
    "host": "commons.wikimedia.org",
    "display_name": "Wikimedia Commons",
    "policy": "download_allowed"
  },
  "title": "Big Buck Bunny",
  "description": "Open movie by the Blender Foundation.",
  "duration_seconds": 596,
  "thumbnail_url": "/api/v1/analyze/0f0f0b9e-6d0e-4a5c-9f4b-2f4a3f0b8f11/thumbnail",
  "published_at": "2008-05-28T00:00:00Z",
  "candidates": [
    {
      "url": "https://upload.wikimedia.org/wikipedia/commons/transcoded/.../Big_Buck_Bunny_medium.ogv.480p.vp9.webm",
      "kind": "video",
      "mime_type": "video/webm",
      "bytes": 15800837,
      "width": 854,
      "height": 480,
      "label": "480p"
    }
  ],
  "download": {
    "allowed": true,
    "reason": "source_download_allowed",
    "max_bytes": 2147483648
  },
  "playback": { "mode": "file", "url": null },
  "warnings": []
}
```

Kasus ditolak (tetap `200`, karena analisis berhasil; unduhan yang tidak diizinkan):

```json
{
  "download": { "allowed": false, "reason": "drm_protected", "max_bytes": 0 },
  "playback": { "mode": "embed", "url": "https://www.youtube-nocookie.com/embed/..." },
  "warnings": ["Konten dilindungi DRM. Unduhan tidak tersedia; pemutaran hanya lewat embed resmi."]
}
```

Aturan: `analyze` **tidak pernah** menulis `media_items` atau file. Hasil disimpan di Redis dengan key `analysis:{user_id}:{analysis_id}` TTL 30 menit.

### 6.4 Contoh: `POST /api/v1/downloads`

```json
{
  "url": "https://upload.wikimedia.org/wikipedia/commons/.../Big_Buck_Bunny_medium.ogv",
  "analysis_id": "0f0f0b9e-6d0e-4a5c-9f4b-2f4a3f0b8f11",
  "title": "Big Buck Bunny",
  "category": "Film"
}
```

Response `202`:

```json
{
  "id": "6c1f0f52-8f4b-4a0e-9a56-3f6c1d2b7e44",
  "state": "queued",
  "url": "https://upload.wikimedia.org/...",
  "bytes_total": null,
  "bytes_done": 0,
  "progress": 0,
  "created_at": "2026-11-06T09:12:00Z"
}
```

Validasi ulang saat membuat job (wajib, jangan percaya klien):

1. Skema `https` (kecuali dev mengaktifkan `ALLOW_HTTP=true`).
2. Host resolve ke IP publik; seluruh IP harus publik.
3. Policy sumber harus `download_allowed`.
4. Ukuran dari `HEAD`/`Content-Length` ≤ `min(source.max_file_bytes, MAX_DOWNLOAD_BYTES)`.
5. Kuota user tersisa ≥ ukuran (atau ukuran tidak diketahui → tolak jika kuota < 200 MB).
6. Tidak ada job aktif dengan `url_hash` sama (partial unique index).

### 6.5 Contoh: `GET /api/v1/media`

Query: `?kind=video&category=Teknologi&q=bunny&favorite=true&collection=<uuid>&sort=recent&limit=24`

```json
{
  "items": [
    {
      "id": "d3e1...",
      "title": "Big Buck Bunny",
      "kind": "video",
      "category": "Film",
      "duration_seconds": 596,
      "width": 854,
      "height": 480,
      "thumbnail_url": "/api/v1/media/d3e1.../thumbnail",
      "stream_url": "/api/v1/media/d3e1.../stream",
      "source": { "host": "commons.wikimedia.org", "display_name": "Wikimedia Commons" },
      "is_favorite": true,
      "progress": { "position_seconds": 132, "completed": false },
      "created_at": "2026-11-06T09:14:03Z"
    }
  ],
  "next_cursor": null
}
```

`sort`: `recent` (default), `title`, `duration`, `last_watched`. Pencarian `q` memakai `title ILIKE` + `similarity()` dari `pg_trgm`; skor diurutkan, bukan full-text bahasa Indonesia.

### 6.6 Contoh: `GET /api/v1/recommendations?surface=home&limit=20`

```json
{
  "generated_at": "2026-11-06T02:00:00Z",
  "items": [
    {
      "media_id": "d3e1...",
      "score": 0.82,
      "reason": "same_category",
      "reason_label": "Karena kamu menonton dokumenter teknologi",
      "title": "Big Buck Bunny",
      "thumbnail_url": "/api/v1/media/d3e1.../thumbnail"
    }
  ]
}
```

`reason` adalah kode stabil: `continue_watching`, `same_category`, `similar_tags`, `recently_added`, `popular_in_library`, `because_favorited`.

### 6.7 SSE progress

`GET /api/v1/downloads/events` → `text/event-stream`

```
event: snapshot
data: {"jobs":[{"id":"6c1f...","state":"downloading","percent":42}]}

event: progress
data: {"id":"6c1f...","state":"downloading","bytes_done":52428800,"bytes_total":158008374,"percent":33}

event: state
data: {"id":"6c1f...","state":"completed","media_id":"d3e1..."}
```

Heartbeat komentar `: ping` setiap 15 detik. Frontend menutup EventSource saat tab hidden dan kembali memakai polling `GET /downloads` (2 detik) sebagai fallback.

### 6.8 Aturan error

Semua error memakai bentuk:

```json
{
  "error": {
    "code": "source_pending_review",
    "message": "Sumber ini belum disetujui untuk diunduh.",
    "details": { "host": "example.com" }
  }
}
```

Daftar lengkap di [Lampiran C](#lampiran-c-kode-error). Pesan `message` ditujukan untuk developer; UI memetakan `code` ke copy bahasa Indonesia.

---

## 7. URL Analyzer

### 7.1 Pipeline

```
input
  → normalize (trim, tambah https bila tanpa skema, buang fragment/utm)
  → scheme check (http/https)
  → host/port check (port 80/443 saja)
  → DNS resolve (A + AAAA) → semua IP harus publik
  → policy lookup (sources)
  → HEAD/GET terbatas (timeout 8s, max 512 KB untuk HTML)
  → sniff content-type + ekstensi + magic bytes
  → cabang:
       direct file  → metadata dari header + ffprobe ringan (opsional)
       HTML page    → OG / JSON-LD / <video> / <img> / oEmbed
       manifest     → HLS/DASH parser
  → deteksi DRM
  → klasifikasi kind + kandidat + policy
  → AnalyzeResult (Redis, TTL 30 menit)
```

### 7.2 Guard SSRF (wajib, test-first)

Blokir semua alamat berikut, baik hasil DNS langsung maupun setelah redirect:

| Kategori | Rentang |
|---|---|
| Unspecified / loopback | `0.0.0.0/8`, `127.0.0.0/8`, `::/128`, `::1/128` |
| Private | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7` |
| Link-local / metadata | `169.254.0.0/16`, `fe80::/10`, `fd00:ec2::254` |
| CGNAT | `100.64.0.0/10` |
| Benchmark / documentation | `198.18.0.0/15`, `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` |
| Multicast / reserved | `224.0.0.0/4`, `240.0.0.0/4`, `ff00::/8` |
| IPv4-mapped IPv6 | `::ffff:0:0/96` (cek IP hasil mapping) |
| Lainnya | port selain 80/443, URL dengan `user:pass@`, host tanpa titik selain `localhost` yang diblokir, panjang URL > 2048 |

Implementasi:

- Resolve sendiri dengan `dnspython`; jangan biarkan `httpx` melakukan resolusi kedua yang berbeda. Simpan daftar IP yang sudah divalidasi, lalu sambungkan ke IP tersebut sambil mempertahankan header `Host` dan SNI.
- Redirect **manual** (maksimal 3). Setiap hop divalidasi ulang dengan aturan yang sama; header `Authorization`/`Cookie` tidak pernah dikirim; method menjadi `GET` bila 303.
- Tolak respons yang bukan `http`/`https`, respons dengan `Content-Length` melebihi batas, dan respons `Transfer-Encoding` aneh.
- Timeout total 8 detik (connect 3 detik), batas 512 KB untuk HTML dan 5 MB untuk probe media.
- Header `User-Agent` jelas: `UniversalVideoHub/0.1 (+https://localhost/bot)`.
- Untuk test, hanya `127.0.0.1` yang boleh diizinkan lewat env `ALLOW_TEST_HOSTS`, dan env itu ditolak saat `ENV=production`.

Pseudocode inti:

```python
async def safe_fetch(url: str, policy: FetchPolicy) -> Fetched:
    current = normalize_url(url)
    for hop in range(policy.max_redirects + 1):
        assert_allowed_scheme(current)
        ips = resolve_public_ips(current.host)      # raise BlockedHost
        async with connect_to(ips[0], sni=current.host) as conn:
            resp = await conn.get(current.path, headers=policy.headers,
                                  timeout=policy.timeout,
                                  max_bytes=policy.max_bytes)
        if resp.is_redirect:
            current = normalize_url(urljoin(current, resp.location))
            continue
        return resp
    raise TooManyRedirects
```

### 7.3 Deteksi tipe

| Input | `kind` | Dasar |
|---|---|---|
| `Content-Type: video/*` atau ekstensi `.mp4/.webm/.mkv/.mov/.ogv` | `video` | header + magic bytes |
| `Content-Type: image/*` atau `.jpg/.png/.webp/.avif/.gif` | `image` | header + Pillow verify (setelah unduh) |
| `.m3u8` / `application/vnd.apple.mpegurl` | `stream` | isi diawali `#EXTM3U` |
| `.mpd` / `application/dash+xml` | `stream` | root `<MPD>` |
| HTML dengan `og:video` / `<video>` / JSON-LD `VideoObject` | `video` atau `stream` | metadata halaman |
| HTML dengan banyak `<img>` kandidat | `image` | galeri, maksimal 20 kandidat |
| HTML lain | `page` | metadata OpenGraph saja |

### 7.4 Ekstraksi metadata

Urutan fallback:

1. **Header HTTP**: `Content-Type`, `Content-Length`, `Content-Disposition` (filename), `Last-Modified`.
2. **OpenGraph**: `og:title`, `og:description`, `og:image`, `og:video`, `og:type`, `og:site_name`.
3. **Twitter Card**: `twitter:title`, `twitter:image`, `twitter:player`.
4. **JSON-LD**: `VideoObject` (`name`, `description`, `thumbnailUrl`, `contentUrl`, `duration`, `uploadDate`), `ImageObject`, `ImageGallery`.
5. **oEmbed** untuk host yang terdaftar (YouTube, Vimeo, SoundCloud bila relevan): hanya metadata + `embed_url`; tidak ada download.
6. **HTML semantic**: `<video src>`, `<source type>`, `<meta property>`.
7. **Nama file** sebagai judul terakhir, di-`humanize` (underscore → spasi, buang hash).

Durasi dinormalisasi ke detik (parser ISO-8601 `PT1H2M3S`). Thumbnail remote **selalu diproksikan** lewat API dan di-cache 24 jam agar tidak membocorkan IP user ke sumber dan tidak kena mixed-content.

### 7.5 Deteksi DRM dan stream

- HLS: baca 64 KB pertama; jika ada `#EXT-X-KEY:METHOD=SAMPLE-AES` atau `METHOD=AES-128` dengan URI lisensi, atau `#EXT-X-SESSION-KEY`, tandai `drm_protected`.
- DASH: `<ContentProtection>` dengan `cenc`/`widevine`/`playready` → `drm_protected`.
- Tanpa DRM: `playback.mode = "hls"` dan `download.allowed = false` pada MVP (mesin segmen belum ada). UI menampilkan badge "Streaming — putar di sumber".
- `youtube.com`, `youtu.be`, `vimeo.com` selalu `embed_only`; `embed_url` memakai domain `youtube-nocookie.com` bila tersedia.

### 7.6 Klasifikasi kategori

Baseline berbasis aturan, bukan model:

```python
CATEGORY_RULES = {
  "Film":        ["movie", "film", "trailer", "short film"],
  "Dokumenter":  ["documentary", "documentary film", "nature", "history"],
  "Edukasi":     ["lecture", "course", "lesson", "explainer", "education"],
  "Musik":       ["music video", "live session", "concert", "album"],
  "Olahraga":    ["highlights", "match", "sport", "training"],
  "Hiburan":     ["comedy", "vlog", "reaction", "podcast"],
  "Teknologi":   ["tech", "programming", "software", "ai", "gadget", "review"],
  "Travel":      ["travel", "drone", "city", "destination"],
  "Gaming":      ["gameplay", "speedrun", "walkthrough", "gaming"],
  "Tutorial":    ["how to", "tutorial", "guide", "step by step"],
}
```

Skor = jumlah bobot kata kunci pada `title + description + tags + channel/author`, dinormalisasi; jika < 0.35 → `Lainnya`, `category_confidence` disimpan. `category_locked = true` setelah user mengoreksi manual; job ingestion berikutnya tidak boleh menimpanya.

---

## 8. Download Engine

### 8.1 State machine

```
                 +-----------+
                 |  queued   |
                 +-----+-----+
                       | worker mengambil job
                       v
                 +-----------+
                 | resolving |---- policy berubah / DRM / terlalu besar
                 +-----+-----+-----------------------------> +---------+
                       |                                      | blocked |
                       v                                      +---------+
                 +-------------+       error sementara              |
                 | downloading |----------------------------+         |
                 +------+------+                            |         |
                        | selesai byte + checksum            |         |
                        v                                   v         |
                 +------------+                        +---------+    |
                 | processing |--- gagal ffprobe ----->| failed  |    |
                 +-----+------+                        +---------+    |
                       | sukses                           ^          |
                       v                                  |          |
                 +-----------+      user cancel           |          |
                 | completed |                    +-------------+    |
                 +-----------+                    |  cancelled  |<---+
                                                  +-------------+
```

Aturan transisi:

| Dari | Ke | Pemicu |
|---|---|---|
| `queued` | `resolving` | worker mulai, ambil lock Redis `lock:job:{id}` |
| `resolving` | `downloading` | HEAD sukses + policy valid + kuota cukup |
| `resolving` | `blocked` | policy bukan `download_allowed`, DRM, ukuran melebihi batas |
| `downloading` | `processing` | byte lengkap + sha256 tersimpan |
| `downloading` | `queued` | error sementara, `attempts < 3`, backoff |
| `downloading` | `failed` | error permanen atau `attempts >= 3` |
| `processing` | `completed` | media_items `ready` |
| `processing` | `failed` | file korup / ffprobe gagal |
| state aktif mana pun | `cancelled` | user membatalkan |
| `failed` | `queued` | user retry manual |

State terminal: `completed`, `failed`, `cancelled`, `blocked`. Job terminal tidak boleh diubah kecuali lewat retry eksplisit (`failed` → `queued`).

### 8.2 Worker

```python
@celery.task(bind=True, max_retries=3, acks_late=True)
def download_job(self, job_id: str) -> None:
    job = claim_job(job_id)                 # SELECT ... FOR UPDATE SKIP LOCKED
    if job is None:
        return
    try:
        plan = resolve_download(job)        # HEAD, policy, kuota
        mark(job, "downloading", bytes_total=plan.size)
        path = stream_to_partial(job, plan) # Range resume + sha256 + progress
        validate_and_finalize(job, path)
        mark(job, "processing")
        process_media.delay(str(job.media_item_id))
    except RetryableError as exc:
        schedule_retry(self, job, exc)
    except PermanentError as exc:
        mark_failed(job, exc.code, str(exc))
    finally:
        release_lock(job)
```

Detail implementasi:

- **Resume**: simpan `.part`; bila ada dan server mendukung `Accept-Ranges: bytes`, kirim `Range: bytes=<size>-`; verifikasi respons `206` dan `Content-Range`. Jika server membalas `200`, mulai dari nol.
- **Retry**: hanya untuk timeout, reset koneksi, `5xx`, `408`, `429` (hormati `Retry-After`). Backoff `2^attempt * 2s + jitter`, maksimal 60 detik, total 3 percobaan. Tidak retry untuk `401/403/404/410`.
- **Batas**: `MAX_DOWNLOAD_BYTES` default 2 GB; `MAX_ACTIVE_JOBS_PER_USER` 3; worker concurrency download 4; total bandwidth dibatasi opsional lewat `DOWNLOAD_RATE_LIMIT_KBPS`.
- **Progress**: update DB maksimal sekali per detik atau setiap 2% (mana yang lebih dulu), di luar itu hanya Redis untuk SSE. Ini mencegah write amplification.
- **Integritas**: hitung `sha256` sambil streaming; bandingkan `Content-Length` bila ada; setelah selesai jalankan `ffprobe -v error -show_format -show_streams` (timeout 30 detik) untuk video dan `Pillow.verify()` untuk gambar.
- **Atomic**: tulis ke `*.part`, `fsync`, rename ke nama final, baru catat `media_files`. Jika proses mati, file orphan dibersihkan job sweep (> 24 jam).
- **Dedupe**: cari `media_files.checksum_sha256` milik user yang sama. Jika ada, hapus file baru, tautkan item ke file lama bila masih dipakai; jika tidak, buat item baru. Job tetap `completed` dengan `duplicate_of` di `audit_log`.
- **Cancel**: set flag `cancel_requested` di Redis; worker memeriksa tiap chunk; hentikan, hapus `.part`, state `cancelled`. Cancel tidak menghapus media yang sudah completed (gunakan `DELETE /media/{id}`).
- **Sweep**: beat task setiap 10 menit menandai job aktif tanpa heartbeat > 15 menit sebagai `failed` dengan `error_code=worker_lost`.

### 8.3 Antrean

| Queue | Task | Concurrency | Timeout |
|---|---|---|---|
| `download` | `download_job` | 4 | 45 menit |
| `process` | `process_media` | 2 | 10 menit |
| `recommend` | `refresh_recommendations` | 1 | 5 menit |
| `beat` | sweep, nightly reco | — | — |

Gunakan Redis DB terpisah untuk broker dan cache (`REDIS_URL` vs `CACHE_URL`) agar `FLUSHDB` cache tidak menghapus antrean.

### 8.4 Penamaan dan layout file

```
media-library/
  u_<user_id>/
    videos/2026/11/<media_id>/original.mp4
    videos/2026/11/<media_id>/thumb.jpg
    videos/2026/11/<media_id>/sprite.jpg
    images/2026/11/<media_id>/original.jpg
    images/2026/11/<media_id>/thumb.webp
    streams/2026/11/<media_id>/metadata.json
```

`storage_key` relatif terhadap `MEDIA_ROOT` (atau prefix bucket). Nama file asli hanya disimpan di metadata, tidak dipakai di path. Ekstensi ditentukan dari MIME hasil sniffing, bukan dari URL.

### 8.5 Batas ukuran dan kuota

- Default kuota per user: 20 GB (`USER_QUOTA_BYTES`).
- Cek kuota dua kali: saat membuat job (perkiraan) dan saat finalisasi (aktual).
- Jika kuota habis: `507 storage_quota_exceeded`, job `blocked`, UI menawarkan hapus media lama.
- `HEAD` tanpa `Content-Length`: izinkan dengan batas streaming `MAX_DOWNLOAD_BYTES`; jika terlampaui di tengah jalan, batalkan dan hapus `.part`.

---

## 9. Media Ingestion dan Processing

### 9.1 Alur

```
file final
  → ffprobe (durasi, codec, resolusi, bitrate, streams)
  → validasi (minimal satu video stream / image valid)
  → thumbnail:
       video: frame pada 10% durasi, maks 1280px, JPEG q=82
       image: resize maks 1280px, WebP q=82
  → metadata media_items (durasi, width, height, language)
  → auto-tag + kategori (aturan §7.6)
  → media_items.status = ready
  → invalidasi cache rekomendasi user
```

Untuk `image` tanpa ffprobe, gunakan Pillow: buka, `verify()`, lalu `ImageOps.exif_transpose`, strip EXIF (privasi), simpan ulang.

### 9.2 Thumbnail video

```bash
ffmpeg -ss <10% durasi> -i input -frames:v 1 -vf "scale='min(1280,iw)':-2" -q:v 3 thumb.jpg
```

Jika gagal (video pendek/rusak), fallback ke frame 0. Jika tetap gagal, `status = failed` dan file dihapus; job `failed` dengan `error_code=unprocessable_media`.

### 9.3 Kategori dan tag

- Kategori wajib salah satu dari 11 kategori masterplan.
- Tag topik opsional (maks 12), diekstrak dari kata kunci judul/deskripsi yang sudah dibersihkan stopword Indonesia/Inggris.
- `category_confidence < 0.35` → `Lainnya`, tetapi UI menampilkan tombol "Koreksi kategori".
- Koreksi manual mengeset `category_locked` dan menambahkan tag `manual`.

### 9.4 Upload lokal

`POST /media/upload` (multipart, maks 2 GB):

1. Streaming ke temp file sambil menghitung sha256 dan ukuran; tolak jika melebihi kuota.
2. Sniff MIME dari magic bytes; tolak selain `video/*` dan `image/*` (dan subtitle `.srt/.vtt` sebagai lampiran **[P1]**).
3. Buat `media_items` (`source_url = "upload://<filename>"`, `canonical_url = "upload://<sha256>"`, `kind` sesuai tipe, `status=processing`).
4. Simpan file ke storage, buat `media_files` role `original`, enqueue `process_media`.
5. Duplikat berdasarkan sha256 mengembalikan `409 conflict_duplicate` dengan `media_id` yang sudah ada.

Upload tidak memakai `download_jobs`; job hanya untuk URL.

---

## 10. Recommendation Engine

### 10.1 Sinyal yang dipakai (Phase 5)

| Sinyal | Sumber | Bobot awal |
|---|---|---|
| Kemiripan konten (kategori + tag) | `media_items`, `media_item_tags` | 0.35 |
| Afinitas tag | agregat tag dari riwayat & favorit | 0.20 |
| Kebaruan | `created_at` | 0.15 |
| Penyelesaian tontonan | `watch_history.completed` / rasio posisi | 0.15 |
| Favorit | `favorites` | 0.10 |
| Kebaruan bagi user | belum pernah ditonton | 0.05 |

Rumus:

```
score = 0.35 * cosine(item_vector, user_vector)
      + 0.20 * tag_affinity
      + 0.15 * exp(-age_days / 30)
      + 0.15 * completion_affinity
      + 0.10 * favorite_affinity
      + 0.05 * novelty
```

`user_vector` = rata-rata bobot kategori/tag dari item yang ditonton ≥ 20% atau difavoritkan, dengan decay `0.9^(minggu sejak interaksi)`.

### 10.2 Baseline tanpa model

Vektor = sparse map `{category: 1.0, tag: 0.6, duration_bucket: 0.2}`. Cosine dihitung di Python; kandidat dibatasi 200 item terbaru milik user agar O(n) tetap murah. Tidak perlu pgvector pada MVP.

### 10.3 Keragaman

Ambil top 50 kandidat, lalu terapkan MMR (`lambda=0.7`) agar 20 hasil tidak semuanya kategori yang sama. Maksimal 6 item per kategori di surface `home`.

### 10.4 Cold start

- 0 interaksi: tampilkan `recently_added` + `popular_in_library` (agregat anonim kategori).
- 1–4 interaksi: 60% kategori dominan, 40% recent.
- ≥ 5 interaksi: skor penuh.

### 10.5 Output dan penjadwalan

- Disimpan di `recommendations` per `(user, media, surface)`; `expires_at = now() + 24 jam`.
- Dihitung oleh beat harian 02:00 dan on-demand `GET /recommendations?refresh=true` (rate limit 1/menit/user).
- Invalidasi: saat media baru `ready`, saat favorit berubah, saat watch history selesai. Invalidasi hanya menghapus baris surface `home`.
- Alasan selalu disimpan (`reason`) agar UI bisa menjelaskan; tidak ada "black box" pada MVP.

### 10.6 Evaluasi

- Offline leave-one-out pada `watch_history`: untuk tiap user, sembunyikan satu item terakhir, ukur Recall@10 dan NDCG@10.
- Ambang rilis: Recall@10 ≥ 0.25 pada data seed sintetis 40 item; jika di bawah itu, perbaiki aturan sebelum menambah model.
- Collaborative filtering baru dipertimbangkan bila ≥ 50 user aktif dan ≥ 20 interaksi/user; sebelumnya datanya terlalu sparse.

---

## 11. Blueprint UI Aplikasi 1: Peach Finder

### 11.1 Karakter visual

- Dark premium hangat: latar hampir hitam dengan undertone ungu, aksen peach.
- Sudut besar (18–24 px), kartu lembut, ruang kosong lega, tipografi tegas.
- Fokus pada satu aksi: tempel URL → analisis → unduh.

Design token:

```css
--bg: #0C0B10;
--surface: #15131B;
--surface-2: #1E1B25;
--peach: #FFB59E;
--peach-strong: #FF8E6E;
--text: #F6F1EC;
--muted: #A79FAF;
--border: rgba(255,255,255,0.08);
--radius-lg: 22px;
--radius-md: 14px;
--font-sans: "Inter", system-ui, sans-serif;
--font-display: "Space Grotesk", "Inter", sans-serif;
```

### 11.2 Peta halaman

| Route | Isi |
|---|---|
| `/` | Analyze bar, recent discoveries, download queue ringkas |
| `/history` | Semua analisis + unduhan, filter status |
| `/downloads/:id` | Detail job: progress, sumber, error, tombol cancel/retry |
| `/settings` | Registry sumber (read-only), kuota, storage, sesi |
| `/login`, `/register` | Auth |

### 11.3 Wireframe dashboard

```
+------------------------------------------------------------------+
|  () Peach Finder        Antrean 3    Buka My Netflix    Fahmi v  |
+------------------------------------------------------------------+
|                                                                  |
|               Tempel tautan. Kami urus sisanya.                  |
|                                                                  |
|   +----------------------------------------------------------+   |
|   | https://                                                  |   |
|   +----------------------------------------------------------+   |
|                                                                  |
|   [ Auto ] [ Video ] [ Gambar ] [ Stream ]        ( Analisis )   |
|                                                                  |
|   Penemuan terbaru                              Lihat semua ->   |
|   +-------------+  +-------------+  +-------------+              |
|   | thumbnail   |  | thumbnail   |  | thumbnail   |              |
|   | 0:42        |  | 12:08       |  | FOTO        |              |
|   | Judul       |  | Judul       |  | Judul       |              |
|   | [Unduh]     |  | [Embed]     |  | [Unduh]     |              |
|   +-------------+  +-------------+  +-------------+              |
|                                                                  |
|   Antrean unduhan                                  3 aktif       |
|   Big Buck Bunny.mp4     ▓▓▓▓▓▓▓▓░░░░  68%   12 MB/s   [x]      |
|   Bali Drone 4K.mp4      ▓▓▓░░░░░░░░░  24%   8 MB/s    [x]      |
+------------------------------------------------------------------+
```

### 11.4 Kartu hasil analisis

Urutan elemen: thumbnail (16:9), badge tipe, judul, sumber + policy badge, durasi/ukuran, lalu aksi.

| Kondisi | Aksi yang tampil |
|---|---|
| `download.allowed = true` | Tombol utama **Unduh**, dropdown kualitas/kandidat |
| `policy = embed_only` | Tombol **Putar di sumber** (buka tab baru/embed) |
| `drm_protected` | Tombol disabled + tooltip "Dilindungi DRM" |
| `policy = pending_review` | Tombol **Ajukan sumber** + penjelasan |
| `kind = page` | Hanya simpan bookmark/metadata **[P1]** |

### 11.5 State dan copy

| State | Tampilan |
|---|---|
| Empty | "Belum ada penemuan. Tempel tautan pertama kamu." |
| Loading analisis | Skeleton kartu + "Menganalisis…" (maks 8 detik) |
| Error jaringan | "Tidak bisa menjangkau sumber. Periksa tautan atau coba lagi." |
| Blocked | "Sumber ini belum diizinkan untuk diunduh. Kamu masih bisa memutarnya di sumber." |
| Kuota habis | "Penyimpanan penuh. Hapus beberapa item untuk melanjutkan." |
| Sukses unduh | Toast "Ditambahkan ke antrean" + tautan ke My Netflix |

### 11.6 Interaksi

- `Enter` di input = analisis; `Cmd/Ctrl+V` langsung memicu analisis bila clipboard berisi URL (dengan konfirmasi visual).
- Progress queue memakai SSE; jika koneksi putus, fallback polling dan tampilkan ikon "menyambung ulang".
- Tombol hapus job hanya untuk state aktif; job selesai diarahkan ke halaman media.
- Semua tombol punya focus ring peach 2 px; target sentuh ≥ 44 px.

---

## 12. Blueprint UI Aplikasi 2: My Netflix

### 12.1 Karakter visual

- Sinematik gelap netral, aksen crimson original (bukan merah Netflix), tipografi rapat.
- Poster 2:3 untuk film/serial, kartu 16:9 untuk video, 1:1 untuk gambar.
- Hover memperbesar kartu 6% dan menampilkan ringkasan + tombol putar.

Design token:

```css
--bg: #08090B;
--surface: #14161A;
--surface-2: #1C1F24;
--accent: #E0443E;
--accent-soft: rgba(224,68,62,0.16);
--text: #F2F2F2;
--muted: #9AA0A6;
--border: rgba(255,255,255,0.07);
--radius: 10px;
--font-sans: "Inter", system-ui, sans-serif;
```

### 12.2 Peta halaman

| Route | Isi |
|---|---|
| `/` | Hero, Lanjutkan Menonton, Baru Diunduh, Rekomendasi, Trending, Film, Video, Koleksi Gambar, Tonton Nanti |
| `/browse/[kind]` | Grid/filter `video`, `image`, `stream`; sub-filter kategori |
| `/search` | Pencarian + filter tipe, kategori, durasi, sumber |
| `/title/[id]` | Detail: hero, metadata, aksi putar/favorit/koleksi, item terkait |
| `/watch/[id]` | Player layar penuh |
| `/collections`, `/collections/[id]` | Koleksi personal |
| `/favorites` | Favorit |
| `/downloads` | Status unduhan (read-only, tautan ke Peach Finder) |
| `/login` | Auth |

### 12.3 Wireframe homepage

```
+------------------------------------------------------------------+
|  MY NETFLIX     Beranda  Film  Video  Gambar  Koleksi     Cari  o |
+------------------------------------------------------------------+
|  HERO: Big Buck Bunny                                            |
|  Film - 9 mnt - Wikimedia Commons                                |
|  [ > Putar ]  [ + Koleksi ]  [ + Favorit ]                       |
+------------------------------------------------------------------+
|  Lanjutkan Menonton                                     >        |
|  [====32%====] [====68%====] [====91%====]                       |
+------------------------------------------------------------------+
|  Baru Diunduh                                           >        |
|  [poster] [poster] [poster] [poster] [poster]                    |
+------------------------------------------------------------------+
|  Rekomendasi Untukmu                                    >        |
|  [16:9] [16:9] [16:9] [16:9]                                     |
+------------------------------------------------------------------+
|  Film                                                   >        |
|  [2:3] [2:3] [2:3] [2:3] [2:3]                                   |
+------------------------------------------------------------------+
```

Aturan baris: baris kosong tidak dirender (bukan placeholder kosong). Hero memilih item terakhir ditonton yang belum selesai; jika tidak ada, item terbaru.

### 12.4 Detail dan player

- Detail menampilkan sinopsis, durasi, resolusi, kategori (dengan tombol koreksi), sumber, dan tanggal unduh.
- Player HTML5: kontrol play/pause, seek bar dengan buffer, volume, kecepatan 0.75–2×, subtitle (jika ada), fullscreen, dan tombol "kembali ke detail".
- Simpan posisi tiap 5 detik dan saat `pause`/`beforeunload` lewat `POST /watch-history`. Jika posisi > 95% durasi, `completed = true`.
- Stream memakai `GET /media/{id}/stream` dengan Range; jangan pernah memberi path filesystem ke browser.
- Embed (stream) memakai iframe `youtube-nocookie.com`/`player.vimeo.com` dengan `sandbox` dan `allow` minimal.

### 12.5 Search, filter, dan koleksi

- Search debounce 300 ms, hasil instan dari `GET /media?q=`.
- Filter: tipe, kategori, sumber, durasi (`< 5 mnt`, `5–30`, `> 30`), favorit, koleksi.
- Koleksi: buat, ganti nama, hapus; tambah item lewat dialog dari kartu mana pun. Smart collection **[P1]** memakai `smart_rules`.
- "Tonton Nanti" = koleksi sistem dengan slug `watch-later` yang dibuat otomatis saat pertama dipakai.

### 12.6 Aksesibilitas dan performa

- Kontras teks minimal 4.5:1; semua kontrol bisa dioperasikan keyboard.
- Shortcut: `/` fokus pencarian, `Space` play/pause, `←/→` seek 10 detik, `F` fullscreen, `Esc` tutup modal.
- `prefers-reduced-motion`: matikan hover scale dan transisi hero.
- Thumbnail `loading="lazy"`, `srcset` 320/640/1280; poster placeholder berwarna dominan agar tidak ada layout shift.
- Target LCP < 2.5 detik pada koneksi 4G untuk homepage dengan 40 kartu.

---

## 13. Keamanan, Legal, dan Privasi

### 13.1 Registry sumber

Semua host yang diunduh harus ada di `sources`. Default untuk host tak dikenal: `pending_review` (analisis boleh, unduh diblokir). Perubahan policy hanya lewat CLI admin dan tercatat di `audit_log`:

```bash
uv run python -m app.cli approve-source \
  --host commons.wikimedia.org \
  --policy download_allowed \
  --note "CC-licensed media; ToS reviewed 2026-11-06" \
  --max-bytes 2147483648
```

Aturan review: periksa ToS, lisensi konten, dan `robots.txt`; simpan catatan + tanggal. Host `embed_only` tidak pernah masuk jalur unduh meskipun URL terlihat seperti file langsung (cek host, bukan ekstensi).

### 13.2 Auth dan session

- Password: Argon2id (`time_cost=3`, `memory_cost=64 MiB`, `parallelism=4`); minimal 10 karakter; cek daftar password umum.
- Session token: 32 byte acak, disimpan sebagai SHA-256; cookie `uvh_session`, `HttpOnly`, `SameSite=Lax`, `Secure` di prod, umur 30 hari, dirotasi saat login.
- Logout mencabut session di DB; semua session dicabut saat password berubah.
- CSRF: `SameSite=Lax` + validasi `Origin` untuk mutasi; tidak menerima `Content-Type: text/plain` untuk JSON.
- Login rate limit 10/menit/IP dan 5/menit/email; respons tetap generik agar tidak membocorkan keberadaan akun.

### 13.3 Otorisasi

- Semua query media/job/koleksi memakai `WHERE user_id = :current_user`.
- Endpoint file memeriksa kepemilikan `media_item` sebelum membuka storage.
- `download_jobs.media_item_id` hanya diisi setelah proses selesai; jangan pernah menerima `media_id` dari klien untuk job baru.
- Signed URL tidak diperlukan pada MVP karena cookie same-origin; bila storage S3 dipakai, gunakan presigned URL 5 menit untuk thumbnail.

### 13.4 Header dan hardening

```
Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:;
  media-src 'self'; frame-src https://www.youtube-nocookie.com https://player.vimeo.com;
  style-src 'self' 'unsafe-inline'; script-src 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Permissions-Policy: camera=(), microphone=(), geolocation=()
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

- Body limit API: 1 MB JSON; upload streaming dengan batas 2 GB dan timeout.
- Validasi nama file: hanya `[A-Za-z0-9._-]`, dipotong 120 karakter, tidak pernah dipakai sebagai path.
- ffmpeg dijalankan dengan argumen list (bukan shell), timeout, dan `-nostdin`; update rutin karena celah codec.
- Jangan pernah mengeksekusi metadata sebagai HTML; React meng-escape secara default, hindari `dangerouslySetInnerHTML`.

### 13.5 Legal dan takedown

- UI menampilkan checkbox attestation: "Saya berhak mengunduh konten ini dan penggunaannya sesuai lisensi sumber." Dicatat di `audit_log`.
- Halaman `/legal` memuat kebijakan: hanya konten yang diizinkan; tanpa DRM; tanpa bypass paywall; penghormatan ToS.
- Prosedur takedown: kontak di README + halaman legal; permintaan valid → blokir host/item, simpan bukti di `audit_log`, hapus file terkait dalam 24 jam.
- Jangan memakai merek/logo Netflix; "My Netflix" hanya nama kerja internal, ganti sebelum rilis publik.

### 13.6 Privasi

- Data minimum: email, nama tampilan, hash password, riwayat tontonan, file media.
- Tidak ada analytics pihak ketiga pada MVP; metrik hanya lokal.
- Hapus akun = hapus semua media, file storage, session, riwayat, dan rekomendasi; job berjalan dibatalkan.
- Retensi log aplikasi 30 hari; `audit_log` 180 hari.
- Ekspor data **[P1]**: ZIP metadata JSON + daftar file.

---

## 14. Infrastruktur dan Deployment

### 14.1 Docker Compose pengembangan

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: uvh
      POSTGRES_PASSWORD: uvh
      POSTGRES_DB: uvh
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  api:
    build: ./services/api
    env_file: .env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes: ["./services/api:/app", "./media-library:/data/media"]
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
  worker:
    build: ./services/api
    env_file: .env
    command: celery -A app.worker worker -Q download,process -c 4 --loglevel=INFO
    volumes: ["./services/api:/app", "./media-library:/data/media"]
    depends_on: [postgres, redis]
  beat:
    build: ./services/api
    env_file: .env
    command: celery -A app.worker beat --loglevel=INFO
    depends_on: [redis]
volumes:
  pgdata:
```

Frontend dijalankan dengan `pnpm dev` (HMR), bukan di dalam compose.

### 14.2 Quickstart

```bash
cp .env.example .env
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
pnpm install
uv sync --directory services/api
uv run --directory services/api alembic upgrade head
uv run --directory services/api python -m app.cli seed-demo
pnpm --filter video-finder dev     # :3000
pnpm --filter my-netflix dev       # :3001
uv run --directory services/api uvicorn app.main:app --reload  # :8000
```

`seed-demo` membuat: 1 user demo, 5 sumber `download_allowed`, 6 media contoh (4 video, 1 gambar, 1 embed), 2 koleksi, riwayat tontonan sintetis. File contoh diunduh dari Wikimedia/Internet Archive saat seed (butuh internet) atau disalin dari `tests/fixtures/media` untuk mode offline.

### 14.3 Produksi

- Reverse proxy Caddy/Nginx: TLS, `/api` → FastAPI, `/` → Next app sesuai host.
- Cookie domain `.videohub.example` agar kedua subdomain berbagi session; `Secure` wajib.
- Postgres managed + backup harian (`pg_dump`) dan retensi 7 hari; uji restore bulanan.
- Storage lokal harus persisten (volume) dan di-backup terpisah dari DB; atau aktifkan driver S3/MinIO.
- Worker dijalankan sebagai proses terpisah dengan health check `celery inspect ping`.
- Migrasi dijalankan sebagai job satu kali sebelum deploy API baru (bukan saat startup).
- Observability: log JSON (`request_id`, `user_id`, `job_id`, `duration_ms`), metrik Prometheus (`http_request_duration_seconds`, `download_bytes_total`, `job_state_total`, `queue_depth`), error tracking opsional.
- Graceful shutdown worker: `acks_late` + `--max-tasks-per-child=20` untuk membatasi kebocoran memori ffmpeg.

### 14.4 Desktop dan mobile

- **Desktop (Phase 6)**: Tauri membungkus dua frontend; API + worker berjalan sebagai sidecar, Postgres diganti SQLite? **Tidak** — lebih aman mempertahankan Postgres via embedded? Keputusan: desktop mode memakai API lokal dengan Postgres portable atau mode "remote server". Untuk MVP desktop, arahkan Tauri ke API yang sudah ada (remote/local Docker) dan gunakan filesystem lokal untuk storage. Menghindari dua dialek SQL.
- **Mobile [NANTI]**: React Native hanya klien API; tidak ada download engine di perangkat.

---

## 15. Roadmap dan Task Breakdown

Total estimasi: **32 hari kerja** untuk satu developer yang dibantu AI, belum termasuk buffer review.

### Phase 1 — Foundation (5 hari)

| ID | Task | Acceptance |
|---|---|---|
| P1-01 | Monorepo pnpm + uv, lint/format, CI dasar | `pnpm lint`, `ruff`, `pytest` jalan di CI |
| P1-02 | Docker compose Postgres/Redis + Alembic baseline | `alembic upgrade head` membuat semua tabel §5 |
| P1-03 | Auth register/login/logout/me + cookie + rate limit | Test: register → login → akses `/media` → logout ditolak |
| P1-04 | StorageDriver local + konfigurasi kuota | Test simpan/baca/hapus file, path traversal ditolak |
| P1-05 | Dua shell Next.js + design tokens + login | Kedua app bisa login dan menampilkan halaman kosong |

### Phase 2 — URL Discovery (5 hari)

| ID | Task | Acceptance |
|---|---|---|
| P2-01 | `safe_fetch` + SSRF guard + test tabel alamat | Semua kasus §7.2 diblokir; redirect ke private ditolak |
| P2-02 | Deteksi tipe + metadata OG/JSON-LD/header | Fixture HTML/video/image menghasilkan kind dan judul benar |
| P2-03 | oEmbed + embed_only + deteksi DRM | YouTube → `embed_only`; manifest ber-`ContentProtection` → `drm_protected` |
| P2-04 | Registry sumber + policy + CLI approve | Host `pending_review` tidak bisa diunduh |
| P2-05 | Endpoint `/analyze` + cache Redis + proxy thumbnail | p95 < 2.5 detik; cache hit < 100 ms |
| P2-06 | UI analyze + kartu hasil + state blocked/DRM | Alur tempel URL → hasil tampil tanpa reload |

### Phase 3 — Download Engine (7 hari)

| ID | Task | Acceptance |
|---|---|---|
| P3-01 | Model job + endpoint create/list/detail/cancel/retry | Idempotency dan partial unique index bekerja |
| P3-02 | Worker streaming + resume + retry + checksum | File uji 100 MB berhasil; resume setelah putus |
| P3-03 | Progress SSE + fallback polling | UI menampilkan progress berubah tanpa refresh |
| P3-04 | Ingest ffprobe + thumbnail + kategori | Item `ready` punya durasi dan thumbnail |
| P3-05 | Dedupe checksum + kuota + sweep job | Unduh URL sama dua kali → 409; kuota habis → 507 |
| P3-06 | UI queue + halaman job | Cancel menghentikan worker < 5 detik |
| P3-07 | Sinkronisasi ke My Netflix (list API) | Item muncul di app B setelah completed |

### Phase 4 — Netflix Interface (6 hari)

| ID | Task | Acceptance |
|---|---|---|
| P4-01 | Home hero + rows dinamis | Minimal 6 baris dari data nyata; baris kosong hilang |
| P4-02 | Browse + search + filter | Filter kombinasi benar; query < 200 ms @ 10k item |
| P4-03 | Detail + player Range + watch history | Seek berfungsi; posisi tersimpan dan muncul di Continue |
| P4-04 | Favorites + collections CRUD | Favorit idempoten; koleksi bisa diisi/dikosongkan |
| P4-05 | Responsif + aksesibilitas + skeleton | Keyboard-only menyelesaikan alur putar |
| P4-06 | Tonton Nanti + empty states | Semua state punya copy dan CTA |

### Phase 5 — Recommendation (4 hari)

| ID | Task | Acceptance |
|---|---|---|
| P5-01 | Vektor kategori/tag + skor §10 | Unit test skor deterministik |
| P5-02 | Job beat + invalidasi + tabel recommendations | Rekomendasi muncul untuk user dengan riwayat |
| P5-03 | MMR + batas per kategori + alasan | 20 item, maks 6/kategori, alasan tampil di UI |
| P5-04 | Cold start + evaluasi Recall@10 | Recall@10 ≥ 0.25 pada data seed |

### Phase 6 — Hardening & Production (5 hari)

| ID | Task | Acceptance |
|---|---|---|
| P6-01 | Audit IDOR menyeluruh + test matrix | Semua endpoint resource mengembalikan 404 untuk pemilik lain |
| P6-02 | Rate limit, CSP, cookie domain, HTTPS | Checklist security lulus |
| P6-03 | Backup/restore + migrasi + health check | Restore DB ke instance bersih berhasil |
| P6-04 | Observability + error tracking | Log punya request_id/job_id; dashboard metrik dasar |
| P6-05 | Dokumentasi README + demo script + Tauri spike | `scripts/demo-seed.sh` menjalankan alur 10 langkah |

### Urutan demo MVP (wajib lulus sebelum dianggap selesai)

1. Login sebagai demo.
2. Tempel URL Wikimedia → analisis menampilkan judul, durasi, thumbnail.
3. Klik Unduh → job muncul di antrean, progress berjalan.
4. Job selesai → buka My Netflix → item ada di "Baru Diunduh".
5. Putar video, seek ke tengah, kembali → muncul di "Lanjutkan Menonton".
6. Tandai favorit → muncul di Favorit.
7. Buat koleksi "Open Movies" → tambahkan item.
8. Cari judul → hasil muncul.
9. Tempel URL YouTube → tampil embed, tombol unduh tidak ada.
10. Tempel URL host tak dikenal → analisis jalan, unduh diblokir dengan alasan jelas.

---

## 16. Strategi Pengujian

### 16.1 Piramida

| Level | Alat | Cakupan |
|---|---|---|
| Unit | pytest | SSRF guard, parser metadata, klasifikasi, skor rekomendasi, penamaan file |
| Integrasi | pytest + httpx MockTransport + Postgres container | Router + DB + storage sementara; tidak ada jaringan internet |
| Worker | pytest + fixture HTTP server lokal (khusus test) | Resume, retry, cancel, dedupe |
| Kontrak | Schemathesis dari OpenAPI | Semua endpoint tidak 500 untuk input acak |
| E2E | Playwright | Alur demo 10 langkah, dua app |
| Keamanan | pytest + bandit + `pip-audit` | IDOR, path traversal, SSRF, upload palsu |

### 16.2 Kasus wajib

| Kasus | Ekspektasi |
|---|---|
| `http://127.0.0.1:8000` | `blocked_host` |
| `http://169.254.169.254/latest/meta-data` | `blocked_host` |
| `http://[::1]/` | `blocked_host` |
| `http://2130706433/` (IP desimal) | dinormalisasi lalu diblokir |
| URL publik → redirect ke `http://10.0.0.5` | `blocked_host` pada hop kedua |
| Host dengan A publik + AAAA privat | `blocked_host` (semua IP harus publik) |
| URL `.m3u8` berisi `SAMPLE-AES` | `drm_protected`, unduh ditolak |
| YouTube | `embed_only`, tidak ada job |
| Host tak terdaftar | analisis 200, unduh 403 `source_pending_review` |
| User B membuka `/media/{id}` milik A | `404 not_found` (bukan 403, agar tidak membocorkan) |
| Upload file `.exe` dengan MIME palsu | `415 unsupported_media` |
| Nama file `../../etc/passwd` | disanitasi, tidak keluar dari `MEDIA_ROOT` |
| Kuota 20 GB tercapai | `507 storage_quota_exceeded`, tidak ada file parsial tersisa |
| Dua `POST /downloads` paralel URL sama | satu 202, satu 409 `conflict_duplicate` |

### 16.3 Performa

| Metrik | Target |
|---|---|
| `POST /analyze` (cache miss) p95 | < 2.5 detik |
| `POST /analyze` (cache hit) p95 | < 100 ms |
| `GET /media?limit=24` p95 @ 10k item | < 200 ms |
| Time-to-first-byte stream | < 500 ms |
| Throughput unduh | ≥ 80% bandwidth tautan uji |
| Homepage LCP | < 2.5 detik (4G, 40 kartu) |

---

## 17. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| **Legal/takedown** karena pengguna mengunduh konten berhak cipta | Produk diblokir, tanggung jawab hukum | Registry sumber + attestation + takedown + audit; tanpa DRM |
| **SSRF** lewat URL/redirect/DNS rebinding | Akses jaringan internal | Validasi semua IP tiap hop, connect ke IP tervalidasi, port allowlist, test wajib |
| **Path traversal** lewat nama file/header | Baca/tulis file sembarang | Nama file digenerate, bukan dari input; validasi storage_key |
| **Storage penuh** karena video besar | Layanan berhenti | Kuota user, batas ukuran, monitoring disk, hapus grace period |
| **ffmpeg/ffprobe crash atau celah codec** | Worker mati / RCE | Argumen list, timeout, proses terisolasi, update rutin, max-tasks-per-child |
| **Duplikat unduhan** | Boros storage | Unique URL aktif + dedupe sha256 |
| **Sumber memblokir/rate limit** | Analisis gagal | User-Agent jelas, cache, backoff, tidak retry agresif |
| **DRM false negative** | Upaya unduh konten terproteksi | Deteksi manifest + blokir default untuk host streaming; audit manual |
| **Scope creep** (mobile/desktop/AI) | MVP tidak selesai | Non-goals §2.2 dan urutan fase |
| **Kebocoran file antar user** | Privasi | Filter `user_id` di semua query + test IDOR |
| **Session lintas dua app** | Login dua kali | Cookie domain bersama di prod; rewrite same-origin |
| **Rekomendasi tidak relevan** | Fitur tidak dipakai | Explanation + koreksi manual + evaluasi Recall@10 sebelum rilis |

---

## 18. Definition of Done

Blueprint ini dianggap terimplementasi ketika semua ini benar:

1. `docker compose up` + migrasi + seed berjalan dari clone bersih dalam < 10 menit.
2. Dua frontend berjalan di port berbeda, login sekali (prod: cookie domain bersama), dan berbagi data.
3. Alur demo 10 langkah §15 lulus tanpa intervensi manual di database.
4. `pytest` hijau, termasuk seluruh kasus keamanan §16.2; E2E Playwright hijau.
5. Tidak ada endpoint yang membocorkan resource user lain (audit IDOR selesai).
6. `BLUEPRINT.md` dan `README.md` diperbarui bila ada penyimpangan; tidak ada TODO menggantung di kode.
7. Log dan metrik dasar tersedia; job gagal bisa didiagnosis dari `job_id`.
8. Halaman legal, attestation, dan prosedur takedown tersedia.
9. Backup/restore teruji minimal sekali.
10. Tidak ada DRM bypass, tidak ada host `pending_review` yang bisa diunduh.

---

## Lampiran A: Registry Sumber Awal

Nilai awal untuk `seed-demo` (bukan kepastian hukum; setiap host tetap direview):

| Host | Policy | Catatan |
|---|---|---|
| `commons.wikimedia.org` | `download_allowed` | Media berlisensi bebas; atribusi tetap ditampilkan |
| `upload.wikimedia.org` | `download_allowed` | CDN file Wikimedia |
| `archive.org` | `download_allowed` | Periksa lisensi per item; banyak public domain |
| `pexels.com` | `download_allowed` | Lisensi Pexels mengizinkan unduh dan penggunaan |
| `pixabay.com` | `download_allowed` | Lisensi Pixabay |
| `nasa.gov` | `download_allowed` | Mayoritas public domain |
| `youtube.com`, `youtu.be` | `embed_only` | ToS melarang unduhan; hanya embed |
| `vimeo.com` | `embed_only` | Hanya embed untuk akun yang mengizinkan |
| `netflix.com`, `spotify.com`, platform DRM lain | `blocked` | Tidak ada akses/unduhan |
| lainnya | `pending_review` | Default aman |

---

## Lampiran B: Variabel Environment

| Variabel | Default dev | Wajib produksi | Keterangan |
|---|---|---|---|
| `ENV` | `development` | `production` | Mengaktifkan guard ketat |
| `DATABASE_URL` | `postgresql+asyncpg://uvh:uvh@localhost:5432/uvh` | ya | SQLAlchemy async |
| `REDIS_URL` | `redis://localhost:6379/0` | ya | Broker Celery |
| `CACHE_URL` | `redis://localhost:6379/1` | ya | Cache analisis & progress |
| `SESSION_SECRET` | `dev-secret-change-me` | ya | Minimal 32 byte acak |
| `COOKIE_DOMAIN` | kosong | `.videohub.example` | Kosong = host-only (localhost) |
| `STORAGE_DRIVER` | `local` | ya | `local` atau `s3` |
| `MEDIA_ROOT` | `./media-library` | ya | Path absolut di produksi |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | — | jika `s3` | MinIO/S3 |
| `MAX_DOWNLOAD_BYTES` | `2147483648` | ya | 2 GB |
| `USER_QUOTA_BYTES` | `21474836480` | ya | 20 GB |
| `MAX_ACTIVE_JOBS_PER_USER` | `3` | ya | Batas antrean |
| `ANALYZER_TIMEOUT_SECONDS` | `8` | ya | Total fetch |
| `ANALYZER_MAX_HTML_BYTES` | `524288` | ya | 512 KB |
| `ALLOW_HTTP` | `true` (dev) | `false` | Hanya untuk sumber http lokal/uji |
| `ALLOW_TEST_HOSTS` | `127.0.0.1` (test) | kosong | Ditolak bila `ENV=production` |
| `API_URL` (Next) | `http://localhost:8000` | ya | Target rewrite `/api` |
| `NEXT_PUBLIC_SITE_NAME` | `Universal Video Hub` | ya | Branding |
| `FFMPEG_PATH` / `FFPROBE_PATH` | `ffmpeg` / `ffprobe` | ya | Path binary |
| `LOG_LEVEL` | `INFO` | ya | — |
| `SENTRY_DSN` | kosong | tidak | Opsional |

---

## Lampiran C: Kode Error

| Kode | HTTP | Arti | Aksi UI |
|---|---|---|---|
| `invalid_url` | 400 | URL tidak valid/terlalu panjang | Perbaiki input |
| `unsupported_scheme` | 400 | Bukan http/https | Tampilkan pesan |
| `blocked_host` | 403 | IP privat/loopback/metadata | Tolak, jelaskan |
| `too_many_redirects` | 422 | > 3 redirect | Tampilkan pesan |
| `fetch_timeout` | 504 | Sumber tidak merespons | Coba lagi |
| `source_blocked` | 403 | Policy `blocked` | Tidak ada aksi |
| `source_pending_review` | 403 | Host belum disetujui | Tawarkan "Ajukan sumber" |
| `source_embed_only` | 403 | Hanya embed | Tawarkan putar di sumber |
| `drm_protected` | 403 | DRM terdeteksi | Disable unduh |
| `unsupported_media` | 415 | Bukan video/gambar yang didukung | Tampilkan pesan |
| `too_large` | 413 | Melebihi batas sumber/global | Tampilkan batas |
| `storage_quota_exceeded` | 507 | Kuota user habis | Tawarkan hapus media |
| `conflict_duplicate` | 409 | URL/file sudah ada | Tautkan ke item lama |
| `queue_limit` | 429 | Job aktif maksimal | Tunggu / batalkan |
| `rate_limited` | 429 | Terlalu banyak request | `Retry-After` |
| `not_found` | 404 | Resource tidak ada/bukan milik user | Kembali |
| `unauthorized` | 401 | Session tidak valid | Login |
| `invalid_credentials` | 401 | Email/password salah | Pesan generik |
| `forbidden` | 403 | Aksi tidak diizinkan | Pesan |
| `job_not_cancellable` | 409 | Job sudah terminal | Refresh |
| `unprocessable_media` | 422 | File korup/tidak bisa diproses | Hapus & coba sumber lain |
| `worker_lost` | 500 | Worker berhenti saat job | Retry |
| `internal_error` | 500 | Bug server | Tampilkan request ID |

---

**Akhir dokumen.** Perubahan berikutnya harus memperbarui versi di header, menambah entri di riwayat perubahan, dan menyertakan alasan bila menyimpang dari keputusan §1.

### Riwayat perubahan

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 2026-11-06 | Blueprint awal: keputusan produk, arsitektur, skema, API, analyzer, download engine, UI, roadmap, testing |
