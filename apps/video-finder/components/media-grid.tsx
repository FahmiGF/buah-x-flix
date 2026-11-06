import type { MediaItem } from "@/lib/api-types";
import { formatDuration } from "@/lib/api-types";

const KIND_LABEL: Record<string, string> = {
  video: "Video",
  image: "Gambar",
  stream: "Stream",
  page: "Halaman",
};

export function MediaGrid({ items }: { items: MediaItem[] }) {
  if (items.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-white/10 p-6 text-sm text-muted">
        Belum ada media. Analisis tautan di atas untuk mulai mengisi perpustakaan.
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => {
        const libraryUrl = process.env.NEXT_PUBLIC_LIBRARY_URL ?? "http://localhost:3001";
        return (
          <a
            key={item.id}
            href={`${libraryUrl}/title/${item.id}`}
            className="group overflow-hidden rounded-2xl border border-white/10 bg-panel/80 transition hover:border-peach/40"
          >
            <div className="relative aspect-video bg-gradient-to-br from-panel-2 to-ink">
              {item.thumbnail_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={item.thumbnail_url}
                  alt={item.title}
                  className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"
                />
              ) : (
                <div className="grid h-full place-items-center text-[10px] uppercase tracking-[0.2em] text-muted/50">
                  Tanpa pratinjau
                </div>
              )}
              <span className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-0.5 text-[10px] uppercase tracking-wider text-peach">
                {KIND_LABEL[item.kind] ?? item.kind}
              </span>
            </div>
            <div className="p-3">
              <p className="line-clamp-2 text-sm font-medium text-cream">{item.title}</p>
              <p className="mt-1 truncate text-[11px] text-muted">
                {[item.category, formatDuration(item.duration_seconds), item.source.host]
                  .filter(Boolean)
                  .join(" · ") || "Media tersimpan"}
              </p>
            </div>
          </a>
        );
      })}
    </div>
  );
}
