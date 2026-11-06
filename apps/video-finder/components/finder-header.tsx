import { LogoutButton } from "@uvh/ui";

import type { User } from "@/lib/session";

export function FinderHeader({
  user,
  active = "home",
}: {
  user: User;
  active?: "home" | "history";
}) {
  const libraryUrl = process.env.NEXT_PUBLIC_LIBRARY_URL ?? "http://localhost:3001";

  return (
    <header className="border-b border-white/5 bg-ink/70 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div className="flex items-center gap-6">
          <a href="/" className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-peach font-display text-base font-bold text-ink">
              P
            </span>
            <span>
              <span className="block font-display text-sm font-semibold uppercase tracking-[0.24em] text-cream">
                Peach Finder
              </span>
              <span className="block text-[11px] text-muted">Universal video finder</span>
            </span>
          </a>
          <nav className="hidden items-center gap-4 text-xs sm:flex">
            <a
              href="/"
              className={active === "home" ? "text-peach" : "text-muted hover:text-cream"}
            >
              Beranda
            </a>
            <a
              href="/history"
              className={active === "history" ? "text-peach" : "text-muted hover:text-cream"}
            >
              Riwayat
            </a>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={libraryUrl}
            className="rounded-full border border-peach/30 bg-peach/10 px-4 py-1.5 text-xs font-medium text-peach transition hover:bg-peach/15"
          >
            Buka My Netflix →
          </a>
          <span className="hidden rounded-full border border-white/10 px-3 py-1.5 text-xs text-muted sm:inline">
            {user.display_name}
          </span>
          <LogoutButton />
        </div>
      </div>
    </header>
  );
}
