import { LogoutButton } from "@uvh/ui";

import type { User } from "@/lib/session";

const LINKS = [
  { href: "/", label: "Beranda", key: "home" },
  { href: "/browse/video?category=Film", label: "Film", key: "film" },
  { href: "/browse/video", label: "Video", key: "video" },
  { href: "/browse/image", label: "Gambar", key: "image" },
  { href: "/collections", label: "Koleksi", key: "collections" },
  { href: "/favorites", label: "Favorit", key: "favorites" },
];

export function SiteHeader({
  user,
  active = "home",
  query = "",
}: {
  user: User;
  active?: string;
  query?: string;
}) {
  const finderUrl = process.env.NEXT_PUBLIC_FINDER_URL ?? "http://localhost:3000";

  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-cinema/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-4 px-5 py-3 sm:px-8">
        <a href="/" className="text-sm font-black uppercase tracking-[0.3em] text-crimson">
          My Netflix
        </a>

        <nav className="hidden items-center gap-4 text-xs lg:flex">
          {LINKS.map((link) => (
            <a
              key={link.key}
              href={link.href}
              className={
                active === link.key ? "text-silver" : "text-dim transition hover:text-silver"
              }
            >
              {link.label}
            </a>
          ))}
        </nav>

        <form action="/search" className="ml-auto flex min-w-0 flex-1 items-center sm:max-w-xs">
          <input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Cari judul…"
            aria-label="Cari media"
            className="h-9 w-full rounded-l border border-white/10 bg-black/40 px-3 text-xs text-silver outline-none placeholder:text-dim/60 focus:border-crimson/60"
          />
          <button
            type="submit"
            className="h-9 rounded-r border border-l-0 border-white/10 bg-white/5 px-3 text-xs text-dim transition hover:text-silver"
          >
            Cari
          </button>
        </form>

        <div className="flex items-center gap-3">
          <a
            href={finderUrl}
            className="rounded bg-crimson px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-110"
          >
            + Cari media
          </a>
          <span className="hidden text-xs text-dim xl:inline">{user.display_name}</span>
          <LogoutButton />
        </div>
      </div>
    </header>
  );
}
