import { redirect } from "next/navigation";

import { CollectionCreateForm } from "@/components/collection-form";
import { SiteHeader } from "@/components/site-header";
import type { Collection } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function CollectionsPage() {
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

  const collections = (await apiGet<Collection[]>("/collections")) ?? [];

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={session.user} active="collections" />

      <main className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-crimson">
          Koleksi
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-silver">Susun perpustakaanmu.</h1>
        <p className="mt-1 text-xs text-dim">
          Koleksi bersifat pribadi dan bisa diisi dari halaman detail media.
        </p>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-start">
          <div className="grid gap-3 sm:grid-cols-2">
            {collections.length === 0 ? (
              <p className="rounded-lg border border-dashed border-white/10 p-6 text-sm text-dim sm:col-span-2">
                Belum ada koleksi. Buat koleksi pertamamu di samping.
              </p>
            ) : (
              collections.map((collection) => (
                <a
                  key={collection.id}
                  href={`/collections/${collection.id}`}
                  className="group rounded-lg border border-white/10 bg-panel p-5 transition hover:border-crimson/40"
                >
                  <p className="text-lg font-semibold text-silver group-hover:text-white">
                    {collection.title}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-dim">
                    {collection.description ?? "Tanpa deskripsi"}
                  </p>
                  <p className="mt-4 text-[11px] uppercase tracking-wider text-crimson/90">
                    {collection.item_count} media
                  </p>
                </a>
              ))
            )}
          </div>

          <section className="rounded-lg border border-white/10 bg-panel/70 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-silver">
              Koleksi baru
            </h2>
            <p className="mt-1 mb-4 text-xs text-dim">
              Beri nama sesuai suasana: “Malam Film”, “Edukasi”, atau “Referensi”.
            </p>
            <CollectionCreateForm />
          </section>
        </div>
      </main>
    </div>
  );
}
