import { notFound, redirect } from "next/navigation";

import { Player } from "@/components/player";
import { SiteHeader } from "@/components/site-header";
import { formatDuration, type MediaItem } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function WatchPage({ params }: { params: Promise<{ id: string }> }) {
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

  return (
    <div className="min-h-screen bg-black">
      <SiteHeader user={session.user} active="watch" />

      <main className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-8">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <a href={`/title/${media.id}`} className="text-xs text-dim hover:text-silver">
            ← Detail media
          </a>
          <span className="text-[11px] text-dim">
            {media.progress.completed ? "Selesai ditonton" : "Posisi tersimpan otomatis"}
          </span>
        </div>

        <Player media={media} initialPosition={media.progress.position_seconds} />

        <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-silver">{media.title}</h1>
            <p className="mt-1 text-xs text-dim">
              {[
                media.category,
                formatDuration(media.duration_seconds),
                media.source.display_name ?? media.source.host,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {media.description && (
              <p className="mt-3 max-w-3xl text-sm leading-relaxed text-dim">
                {media.description}
              </p>
            )}
          </div>
          <a
            href="/"
            className="rounded border border-white/15 px-4 py-2 text-xs text-silver hover:border-white/35"
          >
            Beranda
          </a>
        </div>
      </main>
    </div>
  );
}
