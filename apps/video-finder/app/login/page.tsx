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
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-6 py-12">
      <div className="grid gap-10 md:grid-cols-[1.1fr_0.9fr] md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-peach font-display text-lg font-bold text-ink">
              P
            </span>
            <p className="font-display text-sm font-semibold uppercase tracking-[0.3em] text-peach">
              Peach Finder
            </p>
          </div>
          <h1 className="mt-8 font-display text-4xl leading-tight text-cream sm:text-5xl">
            Tempel tautan.
            <br />
            Kami urus sisanya.
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-muted">
            Aplikasi pertama dari Universal Video Hub: analisis URL, unduh media yang
            diizinkan, lalu kirim otomatis ke My Netflix.
          </p>
          <div className="mt-8 flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.16em] text-muted">
            <span className="rounded-full border border-white/10 px-3 py-1">Analisis URL</span>
            <span className="rounded-full border border-white/10 px-3 py-1">Antrean unduh</span>
            <span className="rounded-full border border-white/10 px-3 py-1">Registry sumber</span>
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-panel/90 p-6 shadow-2xl shadow-black/40 backdrop-blur sm:p-8">
          <AuthForm appName="Peach Finder" />
          <p className="mt-6 text-center text-xs text-muted">
            Ingin melihat perpustakaan?{" "}
            <Link href={process.env.NEXT_PUBLIC_LIBRARY_URL ?? "http://localhost:3001"} className="text-peach hover:underline">
              Buka My Netflix
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
