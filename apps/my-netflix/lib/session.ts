import { cookies } from "next/headers";

export type StorageUsage = {
  used_bytes: number;
  limit_bytes: number;
  percent: number;
};

export type User = {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  storage: StorageUsage;
};

export type SessionResult =
  | { state: "authenticated"; user: User }
  | { state: "anonymous" }
  | { state: "unreachable" };

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function readSession(): Promise<SessionResult> {
  const jar = await cookies();
  const cookieHeader = jar
    .getAll()
    .map((cookie) => `${cookie.name}=${cookie.value}`)
    .join("; ");

  try {
    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: cookieHeader ? { cookie: cookieHeader } : {},
      cache: "no-store",
    });
    if (response.status === 401) {
      return { state: "anonymous" };
    }
    if (!response.ok) {
      return { state: "unreachable" };
    }
    return { state: "authenticated", user: (await response.json()) as User };
  } catch {
    return { state: "unreachable" };
  }
}
