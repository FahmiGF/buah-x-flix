import { notFound, redirect } from "next/navigation";

import { CollectionPicker } from "@/components/collection-picker";
import { FavoriteButton } from "@/components/favorite-button";
import { MediaRow } from "@/components/media-row";
import { SiteHeader } from "@/components/site-header";
import {
  formatDuration,
  type Collection,
  type MediaItem,
  type MediaList,
} from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function TitlePage({ params }: { params: Promise<{ id: string }> }) {
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

  const media = await apiGet<MediaItem>(`/media/${id}`);
  if (!media) notFound();

  const [collections, related] = await Promise.all([
    apiGet<Collection[]>("/collections"),
    media.category
      ? apiGet<MediaList>(`/media?category=${encodeURIComponent(media.category)}&limit=12`)
      : Promise.resolve(null),
  ]);

  const relatedItems = (related?.items ?? []).filter((item) => item.id !== media.id);
  const percent =
    media.duration_seconds && media.progress.position_seconds
      ? Math.min((media.progress.position_seconds / media.duration_seconds) * 100, 100)
      : 0;

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={session.user} active="title" />

      <main>
        <section className="relative overflow-hidden border-b border-white/5">
          {media.thumbnail_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={media.thumbnail_url}
              alt=""
              aria-hidden
              className="absolute inset-0 h-full w-full object-cover opacity-25 blur-sm"
            />
          ) : null}
          <div className="absolute inset-0 bg-gradient-to-r from-cinema via-cinema/85 to-cinema/40" />

          <div className="relative mx-auto grid w-full max-w-7xl gap-8 px-5 py-10 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div className="overflow-hidden rounded-lg border border-white/10 bg-black shadow-2xl shadow-black/50">
              {media.thumbnail_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={media.thumbnail_url}
                  alt={media.title}
                  className="aspect-video w-full object-cover"
                />
              ) : (
                <div className="grid aspect-video place-items-center bg-gradient-to-br from-panel-2 to-cinema text-xs uppercase tracking-[0.2em] text-dim/60">
                  {media.kind === "image" ? "Gambar" : "Tanpa pratinjau"}
                </div>
              )}
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-dim">
                <span className="rounded border border-white/20 px-2 py-0.5 uppercase tracking-wider text-silver">
                  {media.kind === "image" ? "Gambar" : media.kind === "video" ? "Video" : "Media"}
                </span>
                {media.category && <span>{media.category}</span>}
                {media.duration_seconds ? <span>{formatDuration(media.duration_seconds)}</span> : null}
                {media.width && media.height ? (
                  <span>
                    {media.width}×{media.height}
                  </span>
                ) : null}
              </div>

              <h1 className="mt-3 text-3xl font-semibold leading-tight text-silver sm:text-5xl">
                {media.title}
              </h1>

              {media.description && (
                <p className="mt-4 max-w-2xl text-sm leading-relaxed text-dim">
                  {media.description}
                </p>
              )}

              <p className="mt-3 text-xs text-dim">
                Sumber:{" "}
                <span className="text-silver">
                  {media.source.display_name ?? media.source.host ?? "Unggahan pribadi"}
                </span>
                {" · "}
                Ditambahkan{" "}
                {new Date(media.created_at).toLocaleDateString("id-ID", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>

              {percent > 0 && (
                <div className="mt-4 max-w-md">
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div className="h-full bg-crimson" style={{ width: `${percent}%` }} />
                  </div>
                  <p className="mt-1 text-[11px] text-dim">
                    {Math.round(percent)}% ditonton · {formatDuration(media.progress.position_seconds)} dari{" "}
                    {formatDuration(media.duration_seconds)}
                  </p>
                </div>
              )}

              <div className="mt-6 flex flex-wrap items-center gap-3">
                <a
                  href={`/watch/${media.id}`}
                  className="rounded bg-silver px-5 py-2.5 text-sm font-semibold text-cinema transition hover:bg-white"
                >
                  {percent > 0 ? "▶ Lanjutkan" : media.kind === "image" ? "Lihat gambar" : "▶ Putar"}
                </a>
                <FavoriteButton mediaId={media.id} initial={media.is_favorite} />
              </div>

              <div className="mt-4">
                <CollectionPicker mediaId={media.id} collections={collections ?? []} />
              </div>
            </div>
          </div>
        </section>

        <div className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8">
          {relatedItems.length > 0 && (
            <MediaRow title="Mirip dengan ini" items={relatedItems} />
          )}

          <div className="mt-8 flex flex-wrap gap-4 text-[11px] text-dim">
            <a href="/" className="hover:text-silver">
              ← Kembali ke beranda
            </a>
            <a href="/downloads" className="hover:text-silver">
              Riwayat unduhan
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
