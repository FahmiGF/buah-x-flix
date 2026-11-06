export type MediaKind = "video" | "image" | "stream" | "page";

export type MediaItem = {
  id: string;
  title: string;
  description: string | null;
  kind: MediaKind;
  category: string | null;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  embed_url: string | null;
  thumbnail_url: string | null;
  stream_url: string | null;
  source: { host: string | null; display_name: string | null };
  is_favorite: boolean;
  progress: { position_seconds: number; completed: boolean };
  created_at: string;
};

export type MediaList = {
  items: MediaItem[];
  total: number;
  limit: number;
  offset: number;
};

export type Analysis = {
  analysis_id: string;
  input_url: string;
  canonical_url: string;
  kind: MediaKind;
  source: { host: string; display_name: string; policy: string };
  title: string;
  description: string | null;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  published_at: string | null;
  candidates: {
    url: string;
    kind: "video" | "image";
    mime_type: string | null;
    bytes: number | null;
    width: number | null;
    height: number | null;
    label: string | null;
  }[];
  download: { allowed: boolean; reason: string; max_bytes: number };
  playback: { mode: "file" | "embed" | "hls" | "none"; url: string | null };
  warnings: string[];
};

export type DownloadJob = {
  id: string;
  state:
    | "queued"
    | "resolving"
    | "downloading"
    | "processing"
    | "completed"
    | "failed"
    | "cancelled"
    | "blocked";
  url: string;
  bytes_total: number | null;
  bytes_done: number;
  progress: number;
  error_code: string | null;
  error_message: string | null;
  media_id: string | null;
  created_at: string;
  finished_at: string | null;
};

export class ApiRequestError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
  }
}

export async function apiSend<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, init);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiRequestError(
      response.status,
      data?.error?.code ?? "request_failed",
      data?.error?.message ?? "Permintaan gagal. Coba lagi.",
    );
  }
  return data as T;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = Math.floor(seconds % 60);
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`
    : `${minutes}:${String(rest).padStart(2, "0")}`;
}
