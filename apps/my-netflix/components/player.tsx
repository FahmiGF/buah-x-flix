"use client";

import { useCallback, useRef } from "react";

import type { MediaItem } from "@/lib/api-types";

export function Player({
  media,
  initialPosition,
}: {
  media: MediaItem;
  initialPosition: number;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const lastSaved = useRef(0);

  const save = useCallback(
    (position: number) => {
      if (!Number.isFinite(position) || position < 0) return;
      void fetch("/api/v1/watch-history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        body: JSON.stringify({
          media_id: media.id,
          position_seconds: Math.floor(position),
          duration_seconds: media.duration_seconds ?? undefined,
        }),
      }).catch(() => undefined);
      lastSaved.current = position;
    },
    [media.duration_seconds, media.id],
  );

  if (media.kind === "image") {
    return (
      <div className="overflow-hidden rounded-lg border border-white/10 bg-black">
        {media.stream_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={media.stream_url}
            alt={media.title}
            className="mx-auto max-h-[75vh] w-auto object-contain"
          />
        ) : (
          <p className="p-10 text-center text-sm text-dim">Berkas gambar tidak tersedia.</p>
        )}
      </div>
    );
  }

  if (!media.stream_url) {
    return (
      <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-8 text-center text-sm text-amber-200">
        Media ini tidak punya berkas lokal.{" "}
        {media.embed_url ? (
          <a href={media.embed_url} target="_blank" rel="noreferrer" className="underline">
            Buka sumber embed ↗
          </a>
        ) : (
          "Coba unduh ulang dari Peach Finder."
        )}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-white/10 bg-black">
      <video
        ref={videoRef}
        src={media.stream_url}
        poster={media.thumbnail_url ?? undefined}
        controls
        playsInline
        preload="metadata"
        className="aspect-video w-full bg-black"
        onLoadedMetadata={(event) => {
          if (initialPosition > 5 && initialPosition < event.currentTarget.duration - 5) {
            event.currentTarget.currentTime = initialPosition;
            lastSaved.current = initialPosition;
          }
        }}
        onTimeUpdate={(event) => {
          const current = event.currentTarget.currentTime;
          if (current - lastSaved.current >= 5) {
            save(current);
          }
        }}
        onPause={(event) => save(event.currentTarget.currentTime)}
        onEnded={(event) => save(event.currentTarget.duration)}
      />
    </div>
  );
}
