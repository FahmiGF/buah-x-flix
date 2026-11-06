import { MediaCard } from "@/components/media-card";
import type { MediaItem } from "@/lib/api-types";

export function MediaGrid({ items, empty }: { items: MediaItem[]; empty?: string }) {
  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-white/10 p-6 text-sm text-dim">
        {empty ?? "Belum ada media di sini."}
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {items.map((item) => (
        <MediaCard key={item.id} item={item} />
      ))}
    </div>
  );
}
