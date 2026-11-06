import { redirect } from "next/navigation";

import { SiteHeader } from "@/components/site-header";
import { formatBytes, type DownloadJob } from "@/lib/api-types";
import { apiGet } from "@/lib/server-api";
import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

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

const STATE_STYLE: Record<string, string> = {
  completed: "text-emerald-300",
  resolving: "text-crimson",
  downloading: "text-crimson",
  processing: "text-crimson",
  queued: "text-dim",
  failed: "text-red-300",
  blocked: "text-amber-300",
  cancelled: "text-dim",
};

export default async function DownloadsPage() {
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

  const jobs = (await apiGet<DownloadJob[]>("/downloads?limit=100")) ?? [];
  const finderUrl = process.env.NEXT_PUBLIC_FINDER_URL ?? "http://localhost:3000";

  return (
    <div className="min-h-screen pb-16">
      <SiteHeader user={session.user} active="downloads" />

      <main className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-crimson">
          Unduhan
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-silver">Riwayat antrean.</h1>
        <p className="mt-1 text-xs text-dim">
          Kelola ulang atau batalkan unduhan aktif dari Peach Finder.
        </p>

        <div className="mt-6 overflow-hidden rounded-lg border border-white/10">
          {jobs.length === 0 ? (
            <p className="bg-panel/60 p-6 text-sm text-dim">
              Belum ada unduhan.{" "}
              <a href={finderUrl} className="text-crimson hover:underline">
                Buka Peach Finder
              </a>
              .
            </p>
          ) : (
            <ul className="divide-y divide-white/5">
              {jobs.map((job) => (
                <li key={job.id} className="bg-panel/60 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span
                      className={`text-[11px] font-semibold uppercase tracking-wider ${
                        STATE_STYLE[job.state] ?? "text-dim"
                      }`}
                    >
                      {STATE_LABEL[job.state] ?? job.state}
                    </span>
                    <span className="text-[11px] text-dim">
                      {formatBytes(job.bytes_done)}
                      {job.bytes_total ? ` / ${formatBytes(job.bytes_total)}` : ""}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-dim" title={job.url}>
                    {job.url}
                  </p>
                  {job.error_message && (
                    <p className="mt-1 text-[11px] text-red-300">{job.error_message}</p>
                  )}
                  <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
                    <div
                      className={`h-full ${job.state === "failed" ? "bg-red-400" : "bg-crimson"}`}
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  {job.media_id && (
                    <a
                      href={`/watch/${job.media_id}`}
                      className="mt-2 inline-block text-[11px] text-crimson hover:underline"
                    >
                      Putar media →
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
