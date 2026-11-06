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

export type Recommendation = {
  media_id: string;
  title: string;
  category: string | null;
  thumbnail_url: string | null;
  reason: string;
  reason_label: string;
  score: number;
};

export type Collection = {
  id: string;
  title: string;
  slug: string;
  description: string | null;
  item_count: number;
  created_at: string;
};

export type CollectionDetail = Collection & { items: MediaItem[] };

export type JobState =
  | "queued"
  | "resolving"
  | "downloading"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled"
  | "blocked";

export type DownloadJob = {
  id: string;
  state: JobState;
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

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return "";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = Math.floor(seconds % 60);
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`
    : `${minutes}:${String(rest).padStart(2, "0")}`;
}
