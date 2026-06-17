"use client";

import { Icon } from "@/components/ui/icon";

// Base do embed do Panda Video (ex.: https://player-vz-XXXX.tv.pandavideo.com.br/embed/).
// Enquanto não configurada, o player mostra um placeholder (o playback real do
// LMS também depende dela).
const PANDA_BASE = process.env.NEXT_PUBLIC_PANDA_EMBED_BASE ?? "";

export function PandaPlayer({
  videoId,
  title,
  playerToken = null,
  drmGroupId = null,
}: {
  videoId: string | null;
  title?: string;
  playerToken?: string | null;
  drmGroupId?: string | null;
}) {
  if (PANDA_BASE && videoId) {
    const sep = PANDA_BASE.includes("?") ? "&" : "?";
    const params = new URLSearchParams({ v: videoId });
    // DRM: embed privado quando o backend assinou um token (mesma lógica do LMS).
    if (playerToken) {
      params.set("watermark", playerToken);
      if (drmGroupId) params.set("drm_group_id", drmGroupId);
    }
    const src = `${PANDA_BASE}${sep}${params.toString()}`;
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
