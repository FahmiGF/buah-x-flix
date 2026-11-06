"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import type { Collection } from "@/lib/api-types";

export function CollectionCreateForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description: description || undefined }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.error?.message ?? "Gagal membuat koleksi.");
      }
      const collection = data as Collection;
      setTitle("");
      setDescription("");
      router.push(`/collections/${collection.id}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal membuat koleksi.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        required
        maxLength={120}
        placeholder="Nama koleksi, mis. Malam Film"
        className="h-10 w-full rounded border border-white/10 bg-black/40 px-3 text-sm text-silver outline-none placeholder:text-dim/60 focus:border-crimson/60"
      />
      <input
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        maxLength={500}
        placeholder="Deskripsi opsional"
        className="h-10 w-full rounded border border-white/10 bg-black/40 px-3 text-sm text-silver outline-none placeholder:text-dim/60 focus:border-crimson/60"
      />
      {error && <p className="text-xs text-red-300">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="rounded bg-crimson px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
      >
        {busy ? "Membuat…" : "Buat koleksi"}
      </button>
    </form>
  );
}
