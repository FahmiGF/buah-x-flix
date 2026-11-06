"use client";

import { useState, type FormEvent } from "react";

const CODE_MESSAGES: Record<string, string> = {
  invalid_credentials: "Email atau password salah.",
  conflict_duplicate: "Email sudah terdaftar. Coba masuk.",
  weak_password: "Password minimal 10 karakter dan tidak terlalu umum.",
  rate_limited: "Terlalu banyak percobaan. Tunggu sebentar lalu coba lagi.",
  validation_error: "Periksa kembali data yang dimasukkan.",
  forbidden: "Permintaan ditolak oleh server.",
};

type Mode = "login" | "register";

export function AuthForm({ appName }: { appName: string }) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    const payload =
      mode === "login"
        ? { email, password }
        : { email, password, display_name: displayName };

    try {
      const response = await fetch(`/api/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        const code: string | undefined = data?.error?.code;
        setError(
          (code && CODE_MESSAGES[code]) ??
            data?.error?.message ??
            "Terjadi kesalahan. Coba lagi.",
        );
        setBusy(false);
        return;
      }

      window.location.assign("/");
    } catch {
      setError("Tidak bisa menghubungi server. Pastikan API berjalan.");
      setBusy(false);
    }
  }

  return (
    <div className="w-full">
      <div className="flex gap-1 rounded-full border border-[var(--border)] bg-[var(--bg)]/60 p-1 text-sm">
        <button
          type="button"
          onClick={() => {
            setMode("login");
            setError(null);
          }}
          aria-pressed={mode === "login"}
          className={`flex-1 rounded-full px-4 py-2 transition ${
            mode === "login"
              ? "bg-[var(--accent)] font-semibold text-black"
              : "text-[var(--muted)] hover:text-[var(--text)]"
          }`}
        >
          Masuk
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("register");
            setError(null);
          }}
          aria-pressed={mode === "register"}
          className={`flex-1 rounded-full px-4 py-2 transition ${
            mode === "register"
              ? "bg-[var(--accent)] font-semibold text-black"
              : "text-[var(--muted)] hover:text-[var(--text)]"
          }`}
        >
          Buat akun
        </button>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {mode === "register" && (
          <label className="block">
            <span className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
              Nama tampilan
            </span>
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
              maxLength={80}
              autoComplete="name"
              placeholder="Nama kamu"
              className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 py-3 text-sm text-[var(--text)] outline-none transition placeholder:text-[var(--muted)]/60 focus:border-[var(--accent)]"
            />
          </label>
        )}

        <label className="block">
          <span className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
            Email
          </span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            placeholder="kamu@example.com"
            className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 py-3 text-sm text-[var(--text)] outline-none transition placeholder:text-[var(--muted)]/60 focus:border-[var(--accent)]"
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
            Password
          </span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={mode === "register" ? 10 : 1}
            maxLength={128}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder={mode === "register" ? "Minimal 10 karakter" : "Password kamu"}
            className="mt-2 w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] px-4 py-3 text-sm text-[var(--text)] outline-none transition placeholder:text-[var(--muted)]/60 focus:border-[var(--accent)]"
          />
        </label>

        {error && (
          <p
            role="alert"
            className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-black transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy
            ? "Memproses…"
            : mode === "login"
              ? `Masuk ke ${appName}`
              : `Buat akun ${appName}`}
        </button>
      </form>

      <p className="mt-4 text-xs leading-relaxed text-[var(--muted)]">
        Sesi disimpan sebagai cookie httpOnly. Tidak ada token di localStorage.
      </p>
    </div>
  );
}
