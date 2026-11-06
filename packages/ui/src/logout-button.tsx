"use client";

import { useState } from "react";

export function LogoutButton() {
  const [busy, setBusy] = useState(false);

  async function logout() {
    setBusy(true);
    try {
      await fetch("/api/v1/auth/logout", { method: "POST" });
    } finally {
      window.location.assign("/login");
    }
  }

  return (
    <button
      type="button"
      onClick={logout}
      disabled={busy}
      className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-[var(--muted)] transition hover:border-white/25 hover:text-[var(--text)] disabled:opacity-50"
    >
      {busy ? "Keluar…" : "Keluar"}
    </button>
  );
}
