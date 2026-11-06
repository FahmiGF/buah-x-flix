import Link from "next/link";
import { redirect } from "next/navigation";
import { AuthForm } from "@uvh/ui";

import { readSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const session = await readSession();
  if (session.state === "authenticated") {
    redirect("/");
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_70%_20%,rgba(224,68,62,0.25),transparent_55%)]" />
      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-6 py-12">
        <div className="grid gap-12 md:grid-cols-[1fr_400px] md:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.5em] text-crimson">
              My Netflix
            </p>
            <h1 className="mt-5 max-w-xl text-4xl font-semibold leading-[1.05] tracking-tight text-silver sm:text-6xl">
              Semua yang kamu simpan.
              <br />
              Satu layar.
            </h1>
            <p className="mt-5 max-w-md text-sm leading-relaxed text-dim">
              Aplikasi kedua Universal Video Hub. Tempat koleksi, riwayat tontonan, dan
              rekomendasi dari media yang sudah kamu simpan.
            </p>
            <div className="mt-8 flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.18em] text-dim">
              <span className="rounded border border-white/10 px-3 py-1">Film</span>
              <span className="rounded border border-white/10 px-3 py-1">Video</span>
              <span className="rounded border border-white/10 px-3 py-1">Gambar</span>
              <span className="rounded border border-white/10 px-3 py-1">Koleksi</span>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-panel/90 p-6 shadow-2xl shadow-black/60 backdrop-blur sm:p-8">
            <AuthForm appName="My Netflix" />
            <p className="mt-6 text-center text-xs text-dim">
              Belum punya koleksi?{" "}
              <Link
                href={process.env.NEXT_PUBLIC_FINDER_URL ?? "http://localhost:3000"}
                className="text-crimson hover:underline"
              >
                Cari media di Peach Finder
              </Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
