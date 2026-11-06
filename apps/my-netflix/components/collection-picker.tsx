"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import type { Collection } from "@/lib/api-types";

export function CollectionPicker({
  mediaId,
  collections,
}: {
  mediaId: string;
  collections: Collection[];
}) {
  const router = useRouter();
  const [selected, setSelected] = useState(collections[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function add() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`/api/v1/collections/${selected}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ media_id: mediaId }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error?.message ?? "Gagal menambahkan ke koleksi.");
      }
      setMessage("Media ditambahkan ke koleksi.");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menambahkan ke koleksi.");
    } finally {
      setBusy(false);
    }
  }

  if (collections.length === 0) {
    return (
      <a href="/collections" className="text-xs text-dim underline-offset-4 hover:text-silver hover:underline">
        Buat koleksi dulu untuk menyimpan media ini.
      </a>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={selected}
        onChange={(event) => setSelected(event.target.value)}
        aria-label="Pilih koleksi"
        className="h-9 rounded border border-white/15 bg-black/40 px-3 text-xs text-silver outline-none focus:border-crimson/60"
      >
        {collections.map((collection) => (
          <option key={collection.id} value={collection.id}>
            {collection.title}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={add}
        disabled={busy}
        className="h-9 rounded border border-white/15 px-3 text-xs text-silver transition hover:border-white/40 disabled:opacity-60"
      >
        {busy ? "Menyimpan…" : "+ Koleksi"}
      </button>
      {message && <span className="text-[11px] text-emerald-300">{message}</span>}
      {error && <span className="text-[11px] text-red-300">{error}</span>}
    </div>
  );
}
