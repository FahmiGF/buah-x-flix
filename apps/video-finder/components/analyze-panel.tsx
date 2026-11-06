"use client";

import { useState, type FormEvent } from "react";

import {
  ApiRequestError,
  apiSend,
  formatBytes,
  formatDuration,
  type Analysis,
  type DownloadJob,
} from "@/lib/api-types";

const ERROR_MESSAGES: Record<string, string> = {
  unsafe_url: "URL ini tidak aman untuk diakses (SSRF guard).",
  source_blocked: "Sumber ini diblokir oleh registry.",
  source_pending_review: "Sumber ini belum disetujui untuk diunduh.",
  source_embed_only: "Sumber ini hanya bisa diputar lewat embed, tidak diunduh.",
  unsupported_url: "Jenis konten di URL ini belum didukung.",
  fetch_failed: "Halaman tidak bisa diambil. Periksa tautan atau coba lagi.",
  too_large: "Konten melebihi batas ukuran yang diizinkan.",
  rate_limited: "Terlalu banyak permintaan. Tunggu sebentar.",
  validation_error: "URL tidak valid. Sertakan http:// atau https://.",
};

const KIND_LABEL: Record<string, string> = {
  video: "Video",
  image: "Gambar",
  stream: "Stream HLS",
  page: "Halaman",
};

const POLICY_LABEL: Record<string, string> = {
  download_allowed: "Boleh diunduh",
  embed_only: "Hanya embed",
  blocked: "Diblokir",
  pending_review: "Menunggu tinjauan",
};

const CATEGORY_BY_KIND: Record<string, string> = {
  video: "Video",
  image: "Gambar",
  stream: "Streaming",
  page: "Lainnya",
};

export function AnalyzePanel({ onQueued }: { onQueued?: (job: DownloadJob) => void }) {
  const [url, setUrl] = useState("");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [candidateIndex, setCandidateIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    setAnalysis(null);
    try {
      const result = await apiSend<Analysis>("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      setAnalysis(result);
      setCandidateIndex(0);
    } catch (err) {
      const code = err instanceof ApiRequestError ? err.code : "request_failed";
      setError(
        ERROR_MESSAGES[code] ?? (err instanceof Error ? err.message : "Analisis gagal."),
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload() {
    if (!analysis) return;
    const candidate = analysis.candidates[candidateIndex];
    if (!candidate) return;
    setDownloading(true);
    setError(null);
    setNotice(null);
    try {
      const job = await apiSend<DownloadJob>("/downloads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: candidate.url,
          analysis_id: analysis.analysis_id,
          title: analysis.title,
          category: CATEGORY_BY_KIND[analysis.kind],
        }),
      });
      setNotice("Unduhan masuk antrean. Pantau progresnya di bawah.");
      onQueued?.(job);
    } catch (err) {
      const code = err instanceof ApiRequestError ? err.code : "request_failed";
      setError(
        ERROR_MESSAGES[code] ?? (err instanceof Error ? err.message : "Gagal memulai unduhan."),
      );
    } finally {
      setDownloading(false);
    }
  }

  const candidate = analysis?.candidates[candidateIndex];
  const canDownload = Boolean(analysis?.download.allowed && analysis.candidates.length > 0);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl text-cream sm:text-3xl">
            Tempel tautan. Kami urus sisanya.
          </h2>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Metadata, pratinjau, dan unduhan hanya untuk sumber yang ada di registry.
            Sumber lain akan ditandai untuk tinjauan.
          </p>
        </div>
        <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] text-muted">
          SSRF-safe · maks {formatBytes(analysis?.download.max_bytes ?? 2 * 1024 ** 3)}
        </span>
      </div>

      <form onSubmit={handleAnalyze} className="mt-6 flex flex-col gap-3 sm:flex-row">
        <input
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          required
          type="url"
          aria-label="URL media"
          placeholder="https://commons.wikimedia.org/wiki/File:..."
          className="h-12 flex-1 rounded-full border border-white/10 bg-black/30 px-5 text-sm text-cream outline-none transition placeholder:text-muted/50 focus:border-peach/60"
        />
        <button
          type="submit"
          disabled={busy}
          className="h-12 rounded-full bg-peach px-6 text-sm font-semibold text-ink transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? "Menganalisis…" : "Analisis URL"}
        </button>
      </form>

      <p className="mt-3 text-[11px] uppercase tracking-[0.18em] text-muted/70">
        Hanya Wikimedia, Archive.org, Pexels, Pixabay, NASA, dan sumber registry lain
      </p>

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200"
        >
          {error}
        </p>
      )}
      {notice && (
        <p className="mt-4 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">
          {notice}
        </p>
      )}

      {analysis && (
        <div className="mt-6 overflow-hidden rounded-2xl border border-white/10 bg-black/20">
          <div className="flex flex-col sm:flex-row">
            <div className="relative aspect-video w-full shrink-0 bg-gradient-to-br from-panel-2 to-ink sm:w-64">
              {analysis.thumbnail_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={analysis.thumbnail_url}
                  alt={analysis.title}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="grid h-full place-items-center text-[10px] uppercase tracking-[0.2em] text-muted/50">
                  Tanpa pratinjau
                </div>
              )}
              <span className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-0.5 text-[10px] uppercase tracking-wider text-peach">
                {KIND_LABEL[analysis.kind] ?? analysis.kind}
              </span>
            </div>

            <div className="flex min-w-0 flex-1 flex-col p-5">
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-muted">
                  {analysis.source.display_name}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 ${
                    analysis.source.policy === "download_allowed"
                      ? "bg-emerald-400/10 text-emerald-200"
                      : "bg-amber-400/10 text-amber-200"
                  }`}
                >
                  {POLICY_LABEL[analysis.source.policy] ?? analysis.source.policy}
                </span>
                {analysis.duration_seconds ? (
                  <span className="text-muted">{formatDuration(analysis.duration_seconds)}</span>
                ) : null}
              </div>

              <h3 className="mt-2 line-clamp-2 font-display text-lg text-cream">
                {analysis.title}
              </h3>
              {analysis.description && (
                <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-muted">
                  {analysis.description}
                </p>
              )}

              {analysis.candidates.length > 1 && (
                <label className="mt-4 block text-xs text-muted">
                  Pilih berkas
                  <select
                    value={candidateIndex}
                    onChange={(event) => setCandidateIndex(Number(event.target.value))}
                    className="mt-1 w-full rounded-xl border border-white/10 bg-ink px-3 py-2 text-sm text-cream outline-none focus:border-peach/60"
                  >
                    {analysis.candidates.map((entry, index) => (
                      <option key={`${entry.url}-${index}`} value={index}>
                        {entry.label ?? entry.mime_type ?? "Berkas"} · {formatBytes(entry.bytes)}
                        {entry.width && entry.height ? ` · ${entry.width}×${entry.height}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              {candidate?.url && (
                <p className="mt-2 truncate text-[11px] text-muted/70">{candidate.url}</p>
              )}

              {analysis.playback.mode === "embed" && analysis.playback.url && (
                <div className="mt-4 overflow-hidden rounded-xl border border-white/10">
                  <iframe
                    src={analysis.playback.url}
                    title={analysis.title}
                    className="aspect-video w-full"
                    allow="accelerometer; encrypted-media; picture-in-picture; fullscreen"
                    referrerPolicy="strict-origin-when-cross-origin"
                    sandbox="allow-scripts allow-same-origin allow-presentation"
                  />
                </div>
              )}

              {analysis.warnings.length > 0 && (
                <ul className="mt-3 space-y-1 text-[11px] text-amber-200/90">
                  {analysis.warnings.map((warning) => (
                    <li key={warning}>• {warning}</li>
                  ))}
                </ul>
              )}

              <div className="mt-auto flex flex-wrap items-center gap-3 pt-4">
                {canDownload ? (
                  <button
                    type="button"
                    onClick={handleDownload}
                    disabled={downloading}
                    className="rounded-full bg-peach px-5 py-2 text-xs font-semibold text-ink transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {downloading ? "Mengantrekan…" : "Unduh ke perpustakaan"}
                  </button>
                ) : (
                  <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-xs text-amber-200">
                    {analysis.download.reason || "Tidak tersedia untuk diunduh"}
                  </span>
                )}
                <a href={analysis.canonical_url} target="_blank" rel="noreferrer" className="text-xs text-muted hover:text-cream">
                  Buka sumber ↗
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
