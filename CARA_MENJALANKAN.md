# Cara Menjalankan Universal Video Hub

Panduan ini menjalankan seluruh sistem secara lokal: PostgreSQL, Redis, API FastAPI,
Peach Finder, dan My Netflix.

## Ringkasan port

| Layanan | URL default |
|---|---|
| API + Swagger | http://127.0.0.1:8000 · http://127.0.0.1:8000/api/docs |
| Peach Finder | http://localhost:3000 |
| My Netflix | http://localhost:3001 |
| PostgreSQL (Docker) | `localhost:55432` |
| Redis (Docker) | `localhost:6379` |

> Di mesin ini port 3000 sedang dipakai proses Node lain. Karena itu Finder dijalankan
> di **3002**; langkah khususnya ada di bagian “Jika port 3000 sudah dipakai”.

## Prasyarat

- Node.js 22+ dan pnpm 12
- Python 3.12+
- Docker Desktop aktif
- `uv` terpasang (`pip install uv`)
- Git Bash (Windows) agar perintah `cp`, `export`, dan path POSIX bekerja

## 1. Siapkan environment dan database

Dari folder `universal-video-hub`:

```bash
cd universal-video-hub

# Sekali saja: buat file environment lokal
cp .env.example .env

# Nyalakan Postgres + Redis
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
docker compose -f infrastructure/docker-compose.yml ps
```

Jika `.env` sudah ada, jangan ditimpa. Pastikan nilainya minimal:

```dotenv
DATABASE_URL=postgresql+asyncpg://uvh:uvh@localhost:55432/uvh
MEDIA_ROOT=media-library
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

Catatan: `.env` di root dibaca oleh backend. Next.js membaca `NEXT_PUBLIC_*` dari
environment command atau `apps/<app>/.env.local`. Nilai default sudah benar untuk
port 3000/3001; untuk port lain, set variabelnya seperti pada langkah khusus di bawah.

## 2. Jalankan backend (terminal 1)

```bash
cd universal-video-hub/services/api
python -m uv sync
python -m uv run alembic upgrade head
python -m uv run python -m app.cli seed-demo
python -m uv run uvicorn app.main:app --reload --port 8000
```

Cek kesiapan:

```bash
curl http://127.0.0.1:8000/api/v1/health/ready
# {"status":"ok","checks":{"database":true,"storage":true}}
```

Biarkan terminal ini tetap berjalan. Swagger ada di
http://127.0.0.1:8000/api/docs.

## 3. Jalankan Peach Finder (terminal 2)

Dari root repo:

```bash
cd universal-video-hub
pnpm install
pnpm dev:finder
```

Buka http://localhost:3000.

## 4. Jalankan My Netflix (terminal 3)

```bash
cd universal-video-hub
pnpm dev:netflix
```

Buka http://localhost:3001.

## 5. Login

Gunakan akun demo yang dibuat oleh `seed-demo`:

```text
Email    : demo@uvh.app
Password : demo-password-2026
```

Login cukup sekali. Kedua aplikasi memakai cookie session yang sama di localhost.

Alur cepat mencoba:

1. Di Peach Finder, tempel URL publik dari sumber yang diizinkan, misalnya
   `https://commons.wikimedia.org/wiki/File:Example.jpg`.
2. Tekan **Analisis**, pilih kandidat, lalu **Unduh**.
3. Tunggu status **Selesai**, lalu tekan **Putar di My Netflix**.
4. Di My Netflix, coba favorit, koleksi, pencarian, dan lanjutkan menonton.

## Jika port 3000 sudah dipakai

Jalankan Finder di 3002 dan izinkan origin tersebut di API.

1. Tambahkan origin ke `.env`:

```dotenv
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002
```

2. Restart backend dari terminal 1 (Ctrl+C, lalu):

```bash
cd universal-video-hub/services/api
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002 \
  python -m uv run uvicorn app.main:app --reload --port 8000
```

3. Finder di 3002, My Netflix tetap di 3001:

```bash
cd universal-video-hub
NEXT_PUBLIC_FINDER_URL=http://localhost:3002 pnpm --filter @uvh/video-finder exec next dev -p 3002
```

4. My Netflix juga perlu tahu URL Finder saat dijalankan:

```bash
cd universal-video-hub
NEXT_PUBLIC_FINDER_URL=http://localhost:3002 pnpm dev:netflix
```

Jika lupa menambahkan origin 3002, login akan gagal dengan
`403 Origin tidak diizinkan`.

## Mode produksi lokal

Environment `NEXT_PUBLIC_*` dibaca saat **build**, jadi set sebelum build:

```bash
cd universal-video-hub
NEXT_PUBLIC_FINDER_URL=http://localhost:3000 \
NEXT_PUBLIC_LIBRARY_URL=http://localhost:3001 \
  pnpm build
```

Jalankan di terminal terpisah:

```bash
pnpm --filter @uvh/my-netflix start     # :3001
pnpm --filter @uvh/video-finder start   # :3000
```

Untuk Finder di 3002:

```bash
NEXT_PUBLIC_FINDER_URL=http://localhost:3002 pnpm build
pnpm --filter @uvh/video-finder exec next start -p 3002
```

## Menjalankan pengecekan

```bash
# Backend (Postgres harus hidup; test memakai database uvh_test)
cd universal-video-hub/services/api
python -m uv run ruff check .
python -m uv run pytest -q

# Frontend
cd universal-video-hub
pnpm build
pnpm typecheck
```

## Berhenti dan mematikan

- Hentikan tiap server dengan `Ctrl+C`.
- Matikan container tanpa menghapus data:

```bash
cd universal-video-hub
docker compose -f infrastructure/docker-compose.yml down
```

Jangan tambahkan `-v` kecuali memang ingin menghapus database dan media.

## Troubleshooting

| Gejala | Penyebab dan solusi |
|---|---|
| `API belum berjalan` di frontend | Backend mati. Jalankan terminal 1 dan cek `/api/v1/health/ready`. |
| Login 403 `Origin tidak diizinkan` | Port frontend tidak ada di `ALLOWED_ORIGINS`. Tambahkan lalu restart API. |
| Login 401 setelah pindah port | Cookie localhost tetap berlaku; pastikan memakai `http://localhost`, bukan campuran `127.0.0.1`. |
| `database connection refused` | Container Postgres belum siap. Cek `docker compose ... ps`; port host adalah 55432. |
| Akun demo tidak ditemukan | Jalankan `python -m uv run python -m app.cli seed-demo`. |
| Port 8000/3000/3001/3002 bentrok | Hentikan proses pemakai port atau ganti port dan sesuaikan `ALLOWED_ORIGINS` serta `NEXT_PUBLIC_*`. |
| Video tidak punya thumbnail | Saat ini thumbnail otomatis hanya dibuat untuk gambar; belum ada ffmpeg/transcoding. |
| Unduhan langsung `failed` setelah API restart | Worker berjalan in-process; job aktif di-sweep menjadi gagal saat startup. Ulangi dari UI. |
| Sumber ditolak `source_pending_review` | Host belum ada di registry. Setujui lewat `python -m uv run python -m app.cli approve-source` setelah meninjau ToS. |
