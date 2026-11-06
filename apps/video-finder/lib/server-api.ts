import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function apiGet<T>(path: string): Promise<T | null> {
  const jar = await cookies();
  const cookieHeader = jar
    .getAll()
    .map((cookie) => `${cookie.name}=${cookie.value}`)
    .join("; ");

  try {
    const response = await fetch(`${API_URL}/api/v1${path}`, {
      headers: cookieHeader ? { cookie: cookieHeader } : {},
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}
