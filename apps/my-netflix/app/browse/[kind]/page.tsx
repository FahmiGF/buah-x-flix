import { notFound, redirect } from "next/navigation";

import { MediaGrid } from "@/components/media-grid";
import { SiteHeader } from "@/components/site-header";
import type { MediaList } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

const KINDS: Record<string, string> = {
  video: "Video",
  image: "Gambar",
  stream: "Stream",
  page: "Halaman",
};

function one(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

export default async function BrowsePage({
  params,
  searchParams,
}: {
  params: Promise<{ kind: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { kind } = await params;
  if (!KINDS[kind]) notFound();

  const query = await searchParams;
  const q = one(query.q).trim();
  const category = one(query.category).trim();
  const sort = one(query.sort) || "recent";

  const session = await readSession();
  if (session.state === "anonymous") redirect(`/login?next=/browse/${kind}`);
  if (session.state === "unreachable") {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="rounded-2xl border border-red-400/20 bg-panel p-8">
          <h1 className="text-2xl font-semibold text-silver">API belum berjalan</h1>
        </div>
      </main>
    );
  }

  const paramsList = new URLSearchParams({ kind, limit: "60", sort });
  if (q) paramsList.set("q", q);
  if (category) paramsList.set("category", category);

  const [data, all] = await Promise.all([
    apiGet<MediaList>(`/media?${paramsList.toString()}`),
    apiGet<MediaList>(`/media?kind=${kind}&limit=100`),
  ]);

  const categories = Array.from(
    new Set((all?.items ?? []).map((item) => item.category).filter(Boolean)),
  ) as string[];
  const items = data?.items ?? [];

  const base = (patch: Record<string, string>) => {
    const next = new URLSearchParams();
    if (q) next.set("q", q);
    if (sort !== "recent") next.set("sort", sort);
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value);
    }
    const queryString = next.toString();
    return `/browse/${kind}${queryString ? `?${queryString}` : ""}`;
  };

  const active = category === "Film" ? "film" : kind;

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={session.user} active={active} query={q} />

      <main className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-crimson">
              Browse
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-silver">
              {category || KINDS[kind]}
            </h1>
            <p className="mt-1 text-xs text-dim">
              {data?.total ?? 0} media{q ? ` untuk “${q}”` : ""}
            </p>
          </div>

          <form action={`/browse/${kind}`} className="flex flex-wrap items-center gap-2">
            {q && <input type="hidden" name="q" value={q} />}
            <select
              name="category"
              defaultValue={category}
              aria-label="Filter kategori"
              className="h-9 rounded border border-white/10 bg-black/40 px-2 text-xs text-silver outline-none focus:border-crimson/60"
            >
              <option value="">Semua kategori</option>
              {categories.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </select>
            <select
              name="sort"
              defaultValue={sort}
              aria-label="Urutan"
              className="h-9 rounded border border-white/10 bg-black/40 px-2 text-xs text-silver outline-none focus:border-crimson/60"
            >
              <option value="recent">Terbaru</option>
              <option value="title">Judul A–Z</option>
              <option value="duration">Durasi terpanjang</option>
            </select>
            <button
              type="submit"
              className="h-9 rounded border border-white/15 px-3 text-xs text-silver hover:border-white/35"
            >
              Terapkan
            </button>
          </form>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <a
            href={base({ category: "" })}
            className={`rounded-full border px-3 py-1 text-[11px] ${
              category
                ? "border-white/10 text-dim hover:text-silver"
                : "border-crimson/50 bg-crimson/10 text-crimson"
            }`}
          >
            Semua
          </a>
          {categories.map((entry) => (
            <a
              key={entry}
              href={base({ category: entry })}
              className={`rounded-full border px-3 py-1 text-[11px] ${
                category === entry
                  ? "border-crimson/50 bg-crimson/10 text-crimson"
                  : "border-white/10 text-dim hover:text-silver"
              }`}
            >
              {entry}
            </a>
          ))}
        </div>

        <div className="mt-6">
          <MediaGrid
            items={items}
            empty={
              q
                ? `Tidak ada hasil untuk “${q}”. Coba kata kunci lain atau unduh media baru.`
                : "Belum ada media di kategori ini. Buka Peach Finder untuk menambah."
            }
          />
        </div>
      </main>
    </div>
  );
}
