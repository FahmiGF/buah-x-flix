import { formatDuration, type MediaItem } from "@/lib/api-types";

const KIND_LABEL: Record<string, string> = {
  video: "Video",
  image: "Gambar",
  stream: "Stream",
  page: "Halaman",
};

export function MediaCard({ item }: { item: MediaItem }) {
  const percent =
    item.duration_seconds && item.progress.position_seconds
      ? Math.min((item.progress.position_seconds / item.duration_seconds) * 100, 100)
      : 0;

  return (
    <a
      href={`/title/${item.id}`}
      className="group block overflow-hidden rounded-md border border-white/5 bg-panel transition duration-200 hover:border-white/20"
    >
      <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-panel-2 to-cinema">
        {item.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.thumbnail_url}
            alt={item.title}
            loading="lazy"
            className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="grid h-full place-items-center text-[10px] uppercase tracking-[0.2em] text-dim/50">
            {KIND_LABEL[item.kind] ?? "Media"}
          </div>
        )}

        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/80 to-transparent" />
        <div className="absolute bottom-2 left-2 flex items-center gap-2">
          <span className="rounded bg-black/70 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-silver">
            {KIND_LABEL[item.kind] ?? item.kind}
          </span>
          {item.duration_seconds ? (
            <span className="text-[10px] text-silver/80">
              {formatDuration(item.duration_seconds)}
            </span>
          ) : null}
        </div>
        {item.is_favorite && (
          <span className="absolute right-2 top-2 text-xs text-crimson" aria-label="Favorit">
            ♥
          </span>
        )}
        {percent > 0 && (
          <div className="absolute inset-x-0 bottom-0 h-0.5 bg-white/20">
            <div className="h-full bg-crimson" style={{ width: `${percent}%` }} />
          </div>
        )}
      </div>
      <div className="p-2.5">
        <p className="line-clamp-2 text-sm font-medium text-silver group-hover:text-white">
          {item.title}
        </p>
        <p className="mt-1 truncate text-[11px] text-dim">
          {item.category ?? item.source.display_name ?? "Media pribadi"}
        </p>
      </div>
    </a>
  );
}
