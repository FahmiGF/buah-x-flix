import { redirect } from "next/navigation";

import { DownloadQueue } from "@/components/download-queue";
import { FinderHeader } from "@/components/finder-header";
import { MediaGrid } from "@/components/media-grid";
import type { DownloadJob, MediaList } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const session = await readSession();

  if (session.state === "anonymous") {
    redirect("/login");
  }

  if (session.state === "unreachable") {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="w-full max-w-lg rounded-3xl border border-red-400/20 bg-panel p-8">
          <h1 className="font-display text-2xl text-cream">API belum berjalan</h1>
          <p className="mt-2 text-sm text-muted">Jalankan backend lalu muat ulang halaman ini.</p>
          <a href="/" className="mt-4 inline-block text-sm text-peach hover:underline">
            Kembali
          </a>
        </div>
      </main>
    );
  }

  const user = session.user;
  const [media, downloads] = await Promise.all([
    apiGet<MediaList>("/media?limit=100"),
    apiGet<DownloadJob[]>("/downloads?limit=50"),
  ]);
  const items = media?.items ?? [];

  return (
    <div className="min-h-screen">
      <FinderHeader user={user} active="history" />

      <main className="mx-auto w-full max-w-6xl px-6 py-10">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-peach">Riwayat</p>
        <h1 className="mt-3 font-display text-3xl text-cream sm:text-4xl">
          Semua yang pernah kamu simpan.
        </h1>
        <p className="mt-2 text-sm text-muted">
          {items.length} media tersimpan · unduhan dan kegagalan tercatat di bawah.
        </p>

        <section className="mt-8 rounded-3xl border border-white/10 bg-panel/80 p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg text-cream">Media tersimpan</h2>
            <span className="text-[11px] text-muted">{items.length} item</span>
          </div>
          <div className="mt-4">
            <MediaGrid items={items} />
          </div>
        </section>

        <section className="mt-6 rounded-3xl border border-white/10 bg-panel/80 p-6">
          <DownloadQueue initialJobs={downloads ?? []} />
        </section>
      </main>
    </div>
  );
}
