import { redirect } from "next/navigation";

import { MediaRow } from "@/components/media-row";
import { SiteHeader } from "@/components/site-header";
import {
  formatBytes,
  formatDuration,
  type MediaItem,
  type MediaList,
  type Recommendation,
} from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function LibraryHome() {
  const session = await readSession();

  if (session.state === "anonymous") {
    redirect("/login");
  }

  if (session.state === "unreachable") {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="w-full max-w-lg rounded-2xl border border-red-400/20 bg-panel p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-red-300">
            API offline
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-silver">Backend belum berjalan</h1>
          <p className="mt-3 text-sm leading-relaxed text-dim">
            Jalankan API dari folder <span className="text-silver">services/api</span>:
          </p>
          <code className="mt-4 block overflow-x-auto rounded-lg border border-white/10 bg-black/40 p-4 text-xs text-crimson">
            python -m uv run uvicorn app.main:app --reload
          </code>
          <a href="/" className="mt-6 inline-block text-sm text-crimson hover:underline">
            Coba lagi
          </a>
        </div>
      </main>
    );
  }

  const user = session.user;
  const finderUrl = process.env.NEXT_PUBLIC_FINDER_URL ?? "http://localhost:3000";

  const [media, continueRows, recommendations, favorites] = await Promise.all([
    apiGet<MediaList>("/media?limit=40"),
    apiGet<MediaItem[]>("/library/continue?limit=12"),
    apiGet<Recommendation[]>("/recommendations?limit=16"),
    apiGet<MediaItem[]>("/favorites"),
  ]);

  const items = media?.items ?? [];
  const resume = continueRows ?? [];
  const recs = recommendations ?? [];
  const hero = resume[0] ?? items[0];

  const films = items.filter((item) => item.category === "Film");
  const images = items.filter((item) => item.kind === "image");
  const videoItems = items.filter((item) => item.kind === "video");

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={user} active="home" />

      <main>
        {hero ? (
          <section className="relative overflow-hidden border-b border-white/5">
            {hero.thumbnail_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={hero.thumbnail_url}
                alt=""
                aria-hidden
                className="absolute inset-0 h-full w-full object-cover opacity-30"
              />
            ) : null}
            <div className="absolute inset-0 bg-gradient-to-r from-cinema via-cinema/80 to-transparent" />
            <div className="absolute inset-0 bg-gradient-to-t from-cinema via-transparent to-transparent" />
            <div className="relative mx-auto w-full max-w-7xl px-5 py-16 sm:px-8 sm:py-24">
              <p className="text-[11px] font-semibold uppercase tracking-[0.4em] text-crimson">
                {hero.progress.position_seconds > 0 ? "Lanjutkan menonton" : "Baru di perpustakaan"}
              </p>
              <h1 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-silver sm:text-6xl">
                {hero.title}
              </h1>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-dim">
                <span className="rounded border border-white/20 px-2 py-0.5 uppercase tracking-wider">
                  {hero.kind === "image" ? "Gambar" : hero.kind === "video" ? "Video" : "Media"}
                </span>
                {hero.category && <span>{hero.category}</span>}
                {hero.duration_seconds ? <span>{formatDuration(hero.duration_seconds)}</span> : null}
                {hero.source.display_name && <span>{hero.source.display_name}</span>}
              </div>
              {hero.description && (
                <p className="mt-4 max-w-xl text-sm leading-relaxed text-dim line-clamp-3">
                  {hero.description}
                </p>
              )}
              <div className="mt-7 flex flex-wrap gap-3">
                <a
                  href={`/watch/${hero.id}`}
                  className="rounded bg-silver px-5 py-2.5 text-sm font-semibold text-cinema transition hover:bg-white"
                >
                  {hero.progress.position_seconds > 0 ? "▶ Lanjutkan" : "▶ Putar"}
                </a>
                <a
                  href={`/title/${hero.id}`}
                  className="rounded border border-white/15 px-5 py-2.5 text-sm text-silver transition hover:border-white/35"
                >
                  Detail
                </a>
              </div>
            </div>
          </section>
        ) : (
          <section className="relative overflow-hidden border-b border-white/5">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_60%_10%,rgba(224,68,62,0.28),transparent_60%)]" />
            <div className="relative mx-auto w-full max-w-7xl px-5 py-16 sm:px-8 sm:py-24">
              <p className="text-[11px] font-semibold uppercase tracking-[0.4em] text-crimson">
                Perpustakaan pribadi
              </p>
              <h1 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-silver sm:text-6xl">
                Layar sudah siap.
                <br />
                Isi dengan koleksimu.
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-relaxed text-dim">
                Belum ada media tersimpan. Buka Peach Finder, tempel tautan dari sumber yang
                diizinkan, lalu unduh. Hasilnya muncul di sini otomatis.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <a
                  href={finderUrl}
                  className="rounded bg-silver px-5 py-2.5 text-sm font-semibold text-cinema transition hover:bg-white"
                >
                  Buka Peach Finder
                </a>
                <a
                  href="/downloads"
                  className="rounded border border-white/15 px-5 py-2.5 text-sm text-dim transition hover:text-silver"
                >
                  Lihat antrean unduhan
                </a>
              </div>
            </div>
          </section>
        )}

        <div className="mx-auto w-full max-w-7xl space-y-9 px-5 py-10 sm:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/5 bg-panel/60 px-5 py-4">
            <div className="flex flex-wrap gap-6 text-xs text-dim">
              <div>
                <p className="text-[11px] uppercase tracking-wider">Media</p>
                <p className="mt-0.5 text-sm text-silver">{media?.total ?? 0} tersimpan</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wider">Lanjutkan</p>
                <p className="mt-0.5 text-sm text-silver">{resume.length} judul</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wider">Favorit</p>
                <p className="mt-0.5 text-sm text-silver">{(favorites ?? []).length} judul</p>
              </div>
            </div>
            <div className="w-full max-w-xs">
              <div className="flex items-center justify-between text-[11px] text-dim">
                <span>Penyimpanan</span>
                <span>
                  {formatBytes(user.storage.used_bytes)} / {formatBytes(user.storage.limit_bytes)}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-crimson"
                  style={{ width: `${Math.min(user.storage.percent, 100)}%` }}
                />
              </div>
            </div>
          </div>

          <MediaRow
            title="Lanjutkan Menonton"
            hint="Posisi tersimpan otomatis saat kamu memutar video."
            items={resume}
          />

          {recs.length > 0 && (
            <section>
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="text-base font-semibold text-silver sm:text-lg">
                  Rekomendasi Untukmu
                </h2>
                <span className="text-[11px] text-dim">Dari kategori & riwayat</span>
              </div>
              <div className="-mx-1 mt-3 flex gap-3 overflow-x-auto px-1 pb-2">
                {recs.map((rec) => (
                  <a
                    key={rec.media_id}
                    href={`/title/${rec.media_id}`}
                    className="group w-44 shrink-0 overflow-hidden rounded-md border border-white/5 bg-panel transition hover:border-white/20 sm:w-52"
                  >
                    <div className="relative aspect-video bg-gradient-to-br from-panel-2 to-cinema">
                      {rec.thumbnail_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={rec.thumbnail_url}
                          alt={rec.title}
                          loading="lazy"
                          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.04]"
                        />
                      ) : (
                        <div className="grid h-full place-items-center text-[10px] uppercase tracking-[0.2em] text-dim/50">
                          Rekomendasi
                        </div>
                      )}
                    </div>
                    <div className="p-2.5">
                      <p className="line-clamp-2 text-sm font-medium text-silver">{rec.title}</p>
                      <p className="mt-1 text-[11px] text-crimson/90">{rec.reason_label}</p>
                    </div>
                  </a>
                ))}
              </div>
            </section>
          )}

          <MediaRow title="Baru Diunduh" href="/browse/video" items={items} />
          <MediaRow title="Film" href="/browse/video?category=Film" items={films} />
          <MediaRow title="Video" href="/browse/video" items={videoItems} />
          <MediaRow title="Koleksi Gambar" href="/browse/image" items={images} />

          {items.length === 0 && (
            <p className="text-xs leading-relaxed text-dim">
              Tip: Wikimedia Commons punya banyak video berlisensi bebas. Tempel halaman
              filenya di Peach Finder untuk melihat kandidat unduhan.
            </p>
          )}

          <footer className="border-t border-white/5 pt-6 text-xs leading-relaxed text-dim">
            Universal Video Hub · My Netflix membaca perpustakaan yang sama dengan Peach
            Finder. Tidak ada DRM yang dilewati.
          </footer>
        </div>
      </main>
    </div>
  );
}
