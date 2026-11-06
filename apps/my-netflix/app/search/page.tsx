import { redirect } from "next/navigation";

import { MediaGrid } from "@/components/media-grid";
import { SiteHeader } from "@/components/site-header";
import type { MediaList } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

function one(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const q = one(query.q).trim();

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

  const data = q
    ? await apiGet<MediaList>(`/media?q=${encodeURIComponent(q)}&limit=60`)
    : null;
  const items = data?.items ?? [];

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={session.user} active="search" query={q} />

      <main className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-crimson">
          Pencarian
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-silver">
          {q ? `Hasil untuk “${q}”` : "Cari di perpustakaanmu"}
        </h1>
        <p className="mt-1 text-xs text-dim">
          {q ? `${data?.total ?? 0} media ditemukan` : "Ketik judul atau deskripsi di kolom pencarian."}
        </p>

        <div className="mt-6">
          <MediaGrid
            items={items}
            empty={
              q
                ? "Tidak ada media yang cocok. Coba kata kunci lain."
                : "Masukkan kata kunci di header untuk mulai mencari."
            }
          />
        </div>
      </main>
    </div>
  );
}
