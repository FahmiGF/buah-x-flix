import { MediaCard } from "@/components/media-card";
import type { MediaItem } from "@/lib/api-types";

export function MediaRow({
  title,
  hint,
  href,
  items,
}: {
  title: string;
  hint?: string;
  href?: string;
  items: MediaItem[];
}) {
  if (items.length === 0) return null;

  return (
    <section>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold text-silver sm:text-lg">{title}</h2>
        {href && (
          <a href={href} className="text-[11px] text-dim transition hover:text-silver">
            Lihat semua →
          </a>
        )}
      </div>
      {hint && <p className="mt-1 text-xs text-dim">{hint}</p>}
      <div className="-mx-1 mt-3 flex gap-3 overflow-x-auto px-1 pb-2">
        {items.map((item) => (
          <div key={item.id} className="w-44 shrink-0 sm:w-52">
            <MediaCard item={item} />
          </div>
        ))}
      </div>
    </section>
  );
}
