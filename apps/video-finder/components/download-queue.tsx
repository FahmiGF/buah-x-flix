"use client";

import { useEffect, useState } from "react";

import { apiSend, formatBytes, type DownloadJob } from "@/lib/api-types";

const ACTIVE_STATES = new Set(["queued", "resolving", "downloading", "processing"]);

const STATE_STYLE: Record<string, string> = {
  queued: "bg-white/5 text-muted",
  resolving: "bg-peach/10 text-peach",
  downloading: "bg-peach/10 text-peach",
  processing: "bg-peach/10 text-peach",
  completed: "bg-emerald-400/10 text-emerald-200",
  failed: "bg-red-400/10 text-red-200",
  blocked: "bg-amber-400/10 text-amber-200",
  cancelled: "bg-white/5 text-muted",
};

const STATE_LABEL: Record<string, string> = {
  queued: "Antre",
  resolving: "Menyiapkan",
  downloading: "Mengunduh",
  processing: "Memproses",
  completed: "Selesai",
  failed: "Gagal",
  blocked: "Diblokir",
  cancelled: "Dibatalkan",
};

const ERROR_LABEL: Record<string, string> = {
  too_large: "Ukuran melebihi batas.",
  source_blocked: "Sumber diblokir.",
  source_pending_review: "Sumber belum disetujui.",
  download_failed: "Unduhan gagal. Coba ulang.",
  checksum_mismatch: "Checksum tidak cocok.",
};

export function DownloadQueue({ initialJobs }: { initialJobs: DownloadJob[] }) {
  const [jobs, setJobs] = useState(initialJobs);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const rows = await apiSend<DownloadJob[]>("/downloads?limit=50", { method: "GET" });
        if (!cancelled) setJobs(rows);
      } catch {
        // Keep the last snapshot when the API is briefly unreachable.
      }
    }

    const timer = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  async function refresh() {
    try {
      setJobs(await apiSend<DownloadJob[]>("/downloads?limit=50", { method: "GET" }));
    } catch {
      // Ignore refresh errors; the poller retries.
    }
  }

  async function cancel(jobId: string) {
    setBusyId(jobId);
    setError(null);
    try {
      await apiSend(`/downloads/${jobId}`, { method: "DELETE" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal membatalkan unduhan.");
    } finally {
      setBusyId(null);
    }
  }

  async function retry(jobId: string) {
    setBusyId(jobId);
    setError(null);
    try {
      await apiSend(`/downloads/${jobId}/retry`, { method: "POST" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengulang unduhan.");
    } finally {
      setBusyId(null);
    }
  }

  const libraryUrl = process.env.NEXT_PUBLIC_LIBRARY_URL ?? "http://localhost:3001";

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg text-cream">Antrean unduhan</h2>
        <span className="text-[11px] text-muted">Diperbarui otomatis</span>
      </div>

      {error && (
        <p role="alert" className="mt-3 rounded-xl border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          {error}
        </p>
      )}

      {jobs.length === 0 ? (
        <p className="mt-4 rounded-2xl border border-dashed border-white/10 p-5 text-sm text-muted">
          Belum ada unduhan. Hasil analisis yang diunduh akan tampil di sini.
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {jobs.map((job) => {
            const active = ACTIVE_STATES.has(job.state);
            return (
              <li key={job.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                      STATE_STYLE[job.state] ?? "bg-white/5 text-muted"
                    }`}
                  >
                    {STATE_LABEL[job.state] ?? job.state}
                  </span>
                  <span className="text-[11px] text-muted">
                    {job.bytes_done > 0 ? formatBytes(job.bytes_done) : "0 B"}
                    {job.bytes_total ? ` / ${formatBytes(job.bytes_total)}` : ""}
                  </span>
                </div>

                <p className="mt-2 truncate text-xs text-muted" title={job.url}>
                  {job.url}
                </p>

                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    className={`h-full rounded-full transition-all ${
                      job.state === "failed" ? "bg-red-400" : "bg-peach"
                    }`}
                    style={{ width: `${Math.max(job.progress, active ? 4 : 0)}%` }}
                  />
                </div>

                {job.error_message && (
                  <p className="mt-2 text-[11px] text-red-200">
                    {ERROR_LABEL[job.error_code ?? ""] ?? job.error_message}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px]">
                  {job.state === "completed" && job.media_id && (
                    <a
                      href={`${libraryUrl}/watch/${job.media_id}`}
                      className="rounded-full bg-peach px-3 py-1 font-semibold text-ink"
                    >
                      Putar di My Netflix →
                    </a>
                  )}
                  {active && (
                    <button
                      type="button"
                      onClick={() => cancel(job.id)}
                      disabled={busyId === job.id}
                      className="text-muted hover:text-red-200 disabled:opacity-50"
                    >
                      Batalkan
                    </button>
                  )}
                  {(job.state === "failed" || job.state === "blocked") && (
                    <button
                      type="button"
                      onClick={() => retry(job.id)}
                      disabled={busyId === job.id}
                      className="rounded-full border border-white/10 px-3 py-1 text-muted hover:text-cream disabled:opacity-50"
                    >
                      Ulangi
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
