import { redirect } from "next/navigation";

import { MediaGrid } from "@/components/media-grid";
import { SiteHeader } from "@/components/site-header";
import type { MediaItem } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function FavoritesPage() {
  const session = await readSession();
  if (session.state === "anonymous") redirect("/login");
  if (session.state === "unreachable") {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="rounded-2xl border border-red-400/20 bg-panel p-8">
          <h1 className="text-2xl font-semibold text-silver">API belum berjalan</h1>
        </div>
      </main>
    );
  }

  const favorites = (await apiGet<MediaItem[]>("/favorites")) ?? [];

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={session.user} active="favorites" />

      <main className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-crimson">
          Favorit
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-silver">Judul yang kamu tandai.</h1>
        <p className="mt-1 text-xs text-dim">{favorites.length} media favorit</p>

        <div className="mt-6">
          <MediaGrid
            items={favorites}
            empty="Belum ada favorit. Buka detail media lalu tekan “Tambah favorit”."
          />
        </div>
      </main>
    </div>
  );
}
