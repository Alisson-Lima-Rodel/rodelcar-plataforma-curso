"use client";

import { Icon } from "@/components/ui/icon";

// Base do embed do Panda Video (ex.: https://player-vz-XXXX.tv.pandavideo.com.br/embed/).
// Enquanto não configurada, o player mostra um placeholder (o playback real do
// LMS também depende dela).
const PANDA_BASE = process.env.NEXT_PUBLIC_PANDA_EMBED_BASE ?? "";

export function PandaPlayer({
  videoId,
  title,
}: {
  videoId: string | null;
  title?: string;
}) {
  if (PANDA_BASE && videoId) {
    const sep = PANDA_BASE.includes("?") ? "&" : "?";
    const src = `${PANDA_BASE}${sep}v=${encodeURIComponent(videoId)}`;
    return (
      <div
        style={{
          aspectRatio: "16 / 9",
          borderRadius: 12,
          overflow: "hidden",
          background: "#000",
        }}
      >
        <iframe
          src={src}
          title={title ?? "Aula"}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
          allowFullScreen
          style={{ width: "100%", height: "100%", border: 0 }}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        aspectRatio: "16 / 9",
        borderRadius: 12,
        background: "linear-gradient(135deg,#1a1f29,#0d1117)",
        border: "1px solid var(--border-strong)",
        display: "grid",
        placeItems: "center",
        textAlign: "center",
      }}
    >
      <div>
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: 9999,
            background: "var(--primary-soft)",
            display: "grid",
            placeItems: "center",
            margin: "0 auto 10px",
          }}
        >
          <Icon name="play" size={28} style={{ color: "var(--primary)" }} />
        </div>
        <p className="tag-mono subtle">{title ?? "Prévia em vídeo"}</p>
      </div>
    </div>
  );
}
