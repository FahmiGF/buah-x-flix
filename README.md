# Universal Video Hub

Dua aplikasi, satu backend: **Peach Finder** untuk menemukan dan menyimpan media yang
diizinkan, dan **My Netflix** untuk menonton serta mengelola perpustakaan pribadi.

Kontrak implementasi lengkap ada di [`BLUEPRINT.md`](./BLUEPRINT.md). Untuk menjalankan
aplikasi langkah demi langkah, baca **[`CARA_MENJALANKAN.md`](./CARA_MENJALANKAN.md)**.

## Status: MVP selesai

| Kapabilitas | Status |
|---|---|
| Monorepo pnpm + uv, CI | ✅ |
| PostgreSQL 16 + migrasi 14 tabel domain | ✅ |
| Auth email/password, session cookie httpOnly, rate limit | ✅ |
| Local storage + proteksi path traversal + kuota | ✅ |
| Analyzer URL dengan guard SSRF dan cache 30 menit | ✅ |
| Registry sumber legal-first (`download_allowed`, `embed_only`, `blocked`) | ✅ |
| Antrean unduhan, progres, cancel, retry, sweep saat startup | ✅ |
| Peach Finder: analisis, pratinjau, unduh, riwayat | ✅ |
| My Netflix: beranda, browse, cari, detail, player, favorit, koleksi, unduhan | ✅ |
| Test backend + build/typecheck frontend | ✅ |

## Fitur

**Peach Finder**

- Tempel URL, lihat judul/deskripsi/thumbnail dan kandidat media.
- Kandidat video/gambar bisa diunduh hanya bila host mengizinkan unduhan.
- YouTube/Vimeo hanya embed; Netflix dan sumber ber-DRM diblokir.
- Antrean unduhan dengan progres, pembatalan, dan pengulangan.
- Riwayat semua media dan unduhan milik akun.

**My Netflix**

- Hero “lanjutkan menonton”, baris media terbaru, rekomendasi, film, video, dan gambar.
- Browse per jenis, filter kategori, urutan, serta pencarian judul.
- Halaman detail dengan favorit dan penambahan ke koleksi.
- Player video dengan posisi tersimpan otomatis setiap 5 detik.
- Koleksi pribadi, favorit, dan riwayat unduhan.

## Prasyarat

- Node.js 22+ dan pnpm 12
- Python 3.12+
- Docker (Postgres + Redis)
- `uv` (`pip install uv`)

## Quickstart

Panduan lengkap: [`CARA_MENJALANKAN.md`](./CARA_MENJALANKAN.md).

```bash
cd universal-video-hub
cp .env.example .env
docker compose -f infrastructure/docker-compose.yml up -d postgres redis

# Terminal 1 — backend
cd services/api
python -m uv sync
python -m uv run alembic upgrade head
python -m uv run python -m app.cli seed-demo
python -m uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — Peach Finder
cd universal-video-hub
pnpm install
pnpm dev:finder    # http://localhost:3000

# Terminal 3 — My Netflix
cd universal-video-hub
pnpm dev:netflix   # http://localhost:3001
```

Login demo: `demo@uvh.app` / `demo-password-2026`.
Kedua aplikasi memakai cookie yang sama di localhost, jadi cukup login sekali.

## Perintah

```bash
# frontend
pnpm build                 # build kedua app
pnpm typecheck             # tsc --noEmit per app

# backend
cd services/api
python -m uv run pytest -q           # butuh Postgres di localhost:55432
python -m uv run ruff check .
python -m uv run alembic upgrade head
python -m uv run python -m app.cli approve-source --host example.com \
  --policy download_allowed --note "ToS reviewed 2026-11-06"
```

Test backend membuat database `uvh_test` sendiri, menjalankan migrasi, lalu
mengosongkan tabel di antara test.

## Struktur

```
apps/video-finder      Peach Finder (Next.js, :3000)
apps/my-netflix        My Netflix (Next.js, :3001)
packages/ui            Auth form + logout bersama
services/api           FastAPI, SQLAlchemy, Alembic, storage
infrastructure         docker-compose Postgres/Redis/API opsional
```

Kedua frontend meneruskan `/api/*` ke FastAPI lewat rewrite Next.js, sehingga cookie
session tetap first-party. Di produksi, set `COOKIE_DOMAIN=.domainmu` agar sesi
dibagikan antar subdomain.

## API

Semua endpoint berada di bawah `/api/v1`; dokumentasi interaktif ada di `/api/docs`.

| Grup | Endpoint utama |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Analyze | `POST /analyze`, `GET /analyze/{id}/thumbnail` |
| Media | `GET/POST /media`, `GET/PATCH/DELETE /media/{id}`, `POST /media/upload`, stream & thumbnail |
| Downloads | `POST/GET /downloads`, `GET/DELETE /downloads/{id}`, `POST /downloads/{id}/retry`, SSE progres |
| Library | `GET/PUT/DELETE /favorites`, `POST/GET /watch-history`, `GET /library/continue` |
| Collections | `GET/POST /collections`, detail, item tambah/hapus |
| Recommendations | `GET /recommendations` |
| Health | `GET /health/live`, `GET /health/ready` |

## Batasan yang disengaja

- Tidak ada bypass DRM atau pengunduhan dari sumber yang tidak disetujui.
- Worker unduhan berjalan in-process (bukan Celery); job aktif ditandai gagal saat
  API restart. Redis belum dipakai untuk antrean.
- Thumbnail otomatis saat ini hanya untuk gambar (JPEG 640 px). Video belum punya
  poster/thumbnail karena belum ada ffmpeg atau transcoding.
- Tidak ada transcoding/HLS lokal; media `stream` hanya diputar lewat embed resmi.
- Pagination media memakai `offset`/`limit`.
- Batas berkas 2 GB per unduhan/upload dan kuota 20 GB per akun.

## Catatan keamanan

- Semua mutasi memeriksa header `Origin`; origin frontend harus terdaftar di
  `ALLOWED_ORIGINS`.
- Session disimpan sebagai hash SHA-256 di database; cookie httpOnly, SameSite=Lax.
- Password memakai Argon2id; minimal 10 karakter dan ditolak bila terlalu umum.
- Storage key tidak pernah berasal dari nama file internet; key divalidasi agar tidak
  keluar dari `MEDIA_ROOT`.
- Analyzer memakai `httpx` dengan resolusi DNS manual, validasi IP pada setiap redirect,
  dan `trust_env=False` untuk mencegah SSRF.
- Registry sumber default `pending_review`; unduhan hanya untuk host yang disetujui.
- Semua query perpustakaan difilter berdasarkan `user_id`.
