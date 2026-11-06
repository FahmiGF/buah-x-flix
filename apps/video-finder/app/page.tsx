import { redirect } from "next/navigation";

import { AnalyzePanel } from "@/components/analyze-panel";
import { DownloadQueue } from "@/components/download-queue";
import { FinderHeader } from "@/components/finder-header";
import { MediaGrid } from "@/components/media-grid";
import { formatBytes, type DownloadJob, type MediaList } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function FinderHome() {
  const session = await readSession();

  if (session.state === "anonymous") {
    redirect("/login");
  }

  if (session.state === "unreachable") {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="w-full max-w-lg rounded-3xl border border-red-400/20 bg-panel p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-red-300">
            API offline
          </p>
          <h1 className="mt-3 font-display text-3xl text-cream">Backend belum berjalan</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Shell frontend aktif, tetapi tidak bisa membaca sesi. Jalankan API dari folder
            <span className="text-cream"> services/api</span>:
          </p>
          <code className="mt-4 block overflow-x-auto rounded-xl border border-white/10 bg-black/40 p-4 text-xs text-peach">
            python -m uv run uvicorn app.main:app --reload
          </code>
          <a href="/" className="mt-6 inline-block text-sm text-peach hover:underline">
            Coba lagi
          </a>
        </div>
      </main>
    );
  }

  const user = session.user;
  const [downloads, recent] = await Promise.all([
    apiGet<DownloadJob[]>("/downloads?limit=50"),
    apiGet<MediaList>("/media?limit=8"),
  ]);

  const used = user.storage.used_bytes;
  const limit = user.storage.limit_bytes;
  const percent = Math.min(user.storage.percent, 100);
  const recentItems = recent?.items ?? [];

  return (
    <div className="min-h-screen">
      <FinderHeader user={user} active="home" />

      <main className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-peach">
              Analyzer · Download · Library
            </p>
            <h1 className="mt-3 font-display text-3xl text-cream sm:text-4xl">
              Halo, {user.display_name.split(" ")[0]}.
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
              Tempel URL, lihat pratinjau, lalu unduh hanya dari sumber yang diizinkan.
              Hasilnya langsung masuk ke My Netflix.
            </p>
          </div>
          <div className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-4 py-2 text-xs text-emerald-200">
            ● {recent?.total ?? 0} media di perpustakaan
          </div>
        </div>

        <section className="relative mt-8 overflow-hidden rounded-[30px] border border-peach/20 bg-gradient-to-br from-[#2b1a20] via-[#19121a] to-ink p-7 sm:p-10">
          <div className="pointer-events-none absolute -right-16 -top-24 h-64 w-64 rounded-full bg-peach/20 blur-3xl" />
          <div className="relative">
            <AnalyzePanel />
          </div>
        </section>

        <div className="mt-6 grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="rounded-3xl border border-white/10 bg-panel/80 p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg text-cream">Penyimpanan</h2>
              <span className="text-[11px] text-muted">
                {formatBytes(used)} / {formatBytes(limit)}
              </span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-peach"
                style={{ width: `${Math.max(percent, used > 0 ? 1 : 0)}%` }}
              />
            </div>
            <p className="mt-2 text-[11px] text-muted">
              {percent}% terpakai · kuota per akun · {user.email}
            </p>

            <div className="mt-5 grid gap-2 text-xs text-muted sm:grid-cols-3">
              {[
                ["1", "Analisis URL dengan guard SSRF"],
                ["2", "Unduh berkas yang diizinkan"],
                ["3", "Putar dari My Netflix"],
              ].map(([step, detail]) => (
                <div key={step} className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <span className="text-peach">{step}</span>
                  <p className="mt-1 leading-relaxed">{detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-white/10 bg-panel/80 p-6">
            <h2 className="font-display text-lg text-cream">Registry sumber</h2>
            <ul className="mt-3 space-y-2 text-xs text-muted">
              <li className="flex items-center justify-between gap-3">
                <span>Wikimedia Commons</span>
                <span className="text-emerald-200">Unduh</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span>Internet Archive · Pexels · Pixabay · NASA</span>
                <span className="text-emerald-200">Unduh</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span>YouTube · Vimeo</span>
                <span className="text-amber-200">Embed</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span>Netflix dan sumber ber-DRM</span>
                <span className="text-red-200">Diblokir</span>
              </li>
            </ul>
            <p className="mt-4 text-[11px] leading-relaxed text-muted/80">
              Hanya konten yang kamu berhak akses. Tidak ada bypass DRM.
            </p>
          </section>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
          <section className="rounded-3xl border border-white/10 bg-panel/80 p-6">
            <DownloadQueue initialJobs={downloads ?? []} />
          </section>

          <section className="rounded-3xl border border-white/10 bg-panel/80 p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg text-cream">Terbaru di perpustakaan</h2>
              <a href="/history" className="text-[11px] text-peach hover:underline">
                Lihat semua →
              </a>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {recentItems.length > 0 ? (
                recentItems.slice(0, 4).map((item) => {
                  const libraryUrl =
                    process.env.NEXT_PUBLIC_LIBRARY_URL ?? "http://localhost:3001";
                  return (
                    <a
                      key={item.id}
                      href={`${libraryUrl}/title/${item.id}`}
                      className="group overflow-hidden rounded-xl border border-white/10 bg-black/20"
                    >
                      <div className="relative aspect-video bg-gradient-to-br from-panel-2 to-ink">
                        {item.thumbnail_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={item.thumbnail_url}
                            alt={item.title}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="grid h-full place-items-center text-[10px] uppercase tracking-[0.2em] text-muted/50">
                            Tanpa pratinjau
                          </div>
                        )}
                      </div>
                      <p className="line-clamp-1 px-3 py-2 text-xs text-cream group-hover:text-peach">
                        {item.title}
                      </p>
                    </a>
                  );
                })
              ) : (
                <p className="text-sm text-muted sm:col-span-2">
                  Belum ada media. Mulai dari tautan Wikimedia Commons di atas.
                </p>
              )}
            </div>
          </section>
        </div>

        <section className="mt-6 rounded-3xl border border-white/10 bg-panel/80 p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg text-cream">Galeri terbaru</h2>
            <a href="/history" className="text-[11px] text-peach hover:underline">
              Riwayat lengkap →
            </a>
          </div>
          <div className="mt-4">
            <MediaGrid items={recentItems} />
          </div>
        </section>

        <p className="mt-6 text-[11px] leading-relaxed text-muted/70">
          Universal Video Hub · Peach Finder hanya mengunduh dari sumber yang diizinkan.
          Media pribadi tetap difilter per akun.
        </p>
      </main>
    </div>
  );
}
