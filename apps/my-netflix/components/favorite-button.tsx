"use client";

import { useState } from "react";

export function FavoriteButton({
  mediaId,
  initial,
}: {
  mediaId: string;
  initial: boolean;
}) {
  const [favorite, setFavorite] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    setBusy(true);
    setError(null);
    const next = !favorite;
    try {
      const response = await fetch(`/api/v1/favorites/${mediaId}`, {
        method: next ? "PUT" : "DELETE",
      });
      if (!response.ok) throw new Error("Gagal memperbarui favorit.");
      setFavorite(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memperbarui favorit.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        disabled={busy}
        aria-pressed={favorite}
        className={`rounded border px-4 py-2 text-sm font-medium transition disabled:opacity-60 ${
          favorite
            ? "border-crimson/50 bg-crimson/15 text-crimson"
            : "border-white/20 text-silver hover:border-white/40"
        }`}
      >
        {favorite ? "♥ Favorit" : "♡ Tambah favorit"}
      </button>
      {error && <p className="mt-1 text-[11px] text-red-300">{error}</p>}
    </div>
  );
}
