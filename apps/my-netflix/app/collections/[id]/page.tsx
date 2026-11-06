import { notFound, redirect } from "next/navigation";

import { MediaGrid } from "@/components/media-grid";
import { SiteHeader } from "@/components/site-header";
import type { CollectionDetail } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function CollectionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
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

  const collection = await apiGet<CollectionDetail>(`/collections/${id}`);
  if (!collection) notFound();

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={session.user} active="collections" />

      <main className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8">
        <a href="/collections" className="text-[11px] text-dim hover:text-silver">
          ← Semua koleksi
        </a>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-crimson">
              Koleksi
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-silver">{collection.title}</h1>
            {collection.description && (
              <p className="mt-2 max-w-2xl text-sm text-dim">{collection.description}</p>
            )}
          </div>
          <span className="text-xs text-dim">{collection.item_count} media</span>
        </div>

        <div className="mt-6">
          <MediaGrid
            items={collection.items}
            empty="Koleksi ini masih kosong. Tambahkan media dari halaman detailnya."
          />
        </div>
      </main>
    </div>
  );
}
