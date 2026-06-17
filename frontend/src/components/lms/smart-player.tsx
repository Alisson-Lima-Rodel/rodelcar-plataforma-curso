"use client";

import { useEffect, useRef } from "react";
import { Icon } from "@/components/ui/icon";

// Base do embed do Panda (ex.: https://player-vz-XXXX.tv.pandavideo.com.br/embed/).
// Sem ela, o player degrada para um placeholder (o playback real depende dela).
const PANDA_BASE = process.env.NEXT_PUBLIC_PANDA_EMBED_BASE ?? "";

// SDK oficial do SmartPlayer (NÃO está sob *.tv.pandavideo.com.br → precisa do
// script-src https://player.pandavideo.com.br na CSP do next.config.mjs).
const SDK_SRC = "https://player.pandavideo.com.br/api.v2.js";

// Controles nativos do SmartPlayer: velocidade, qualidade adaptativa, legendas,
// PiP e fullscreen vêm de graça — basta habilitá-los na barra.
const CONTROLS =
  "play-large,play,progress,current-time,volume,captions,settings,pip,fullscreen,airplay";

// Salva progresso no máximo a cada N ms durante o playback (debounce de rede).
const PING_MS = 7000;
// % a partir da qual a aula é considerada concluída automaticamente.
const CONCLUI_PCT = 95;

/** Atualização de progresso emitida pelo player (consumida pelo LMS). */
export interface ProgressUpdate {
  percentual: number; // 0..100, monotônico (ponto mais distante)
  posicaoSegundos: number; // segundo atual (resume)
  concluida: boolean; // true ao terminar / cruzar CONCLUI_PCT
}

/** Subconjunto da API do SmartPlayer que consumimos. */
interface PandaPlayerInstance {
  onEvent(cb: (e: { message: string; currentTime?: number }) => void): void;
  play(): void;
  pause(): void;
  setCurrentTime(seconds: number): void;
  getCurrentTime(): number;
  getDuration(): number;
  destroy?(): void;
}

declare global {
  interface Window {
    pandascripttag?: Array<() => void>;
    PandaPlayer?: new (
      elementId: string,
      opts: { onReady?: () => void; onError?: (e: unknown) => void },
    ) => PandaPlayerInstance;
  }
}

// Injeta o SDK uma única vez. O Panda usa a fila `window.pandascripttag`: funções
// empurradas antes da carga ficam na fila e rodam quando o script chega; depois
// da carga, rodam imediatamente. Isso cobre SPA (troca de aula reinstancia).
let sdkInjected = false;
function ensureSdk() {
  if (typeof window === "undefined") return;
  window.pandascripttag = window.pandascripttag || [];
  if (sdkInjected || document.querySelector(`script[src="${SDK_SRC}"]`)) {
    sdkInjected = true;
    return;
  }
  sdkInjected = true;
  const s = document.createElement("script");
  s.src = SDK_SRC;
  s.async = true;
  document.head.appendChild(s);
}

function safeNum(fn?: () => number): number {
  try {
    const v = fn?.();
    return typeof v === "number" && isFinite(v) ? v : 0;
  } catch {
    return 0;
  }
}

function Placeholder({ title }: { title?: string }) {
  return (
    <div className="video-stage">
      <div style={{ textAlign: "center", position: "relative", zIndex: 1 }}>
        <div
          className="play-btn"
          style={{
            width: 64,
            height: 64,
            background: "var(--primary-soft)",
            color: "var(--primary)",
            margin: "0 auto 10px",
          }}
        >
          <Icon name="play" size={28} />
        </div>
        <p className="tag-mono subtle">{title ?? "Vídeo indisponível"}</p>
      </div>
    </div>
  );
}

/**
 * Player de aula do LMS sobre o SmartPlayer do Panda. Renderiza o iframe do embed
 * (com controles nativos) e anexa a instância PandaPlayer para receber eventos e
 * controlar o playback. Resume via `startAt` (query-param startTime); progresso
 * contínuo via `onProgress` (eventos timeupdate/pause/ended, com debounce).
 */
export function SmartPlayer({
  videoId,
  title,
  startAt = 0,
  durationSeconds = 0,
  playerToken = null,
  drmGroupId = null,
  onProgress,
}: {
  videoId: string | null;
  title?: string;
  startAt?: number;
  durationSeconds?: number;
  playerToken?: string | null;
  drmGroupId?: string | null;
  onProgress?: (p: ProgressUpdate) => void;
}) {
  const playerRef = useRef<PandaPlayerInstance | null>(null);
  const onProgressRef = useRef(onProgress);
  const durationRef = useRef(durationSeconds);
  onProgressRef.current = onProgress;
  durationRef.current = durationSeconds;

  useEffect(() => {
    if (!PANDA_BASE || !videoId) return;
    ensureSdk();
    const elId = `panda-${videoId}`;
    let cancelled = false;

    // Estado de tracking, reiniciado a cada aula (init roda por videoId).
    let maxPct = 0;
    let concluded = false;
    let lastSent = 0;

    const init = () => {
      if (cancelled || !window.PandaPlayer) return;
      // O 1º arg é o id do iframe já no DOM; o src dele já carrega o vídeo.
      const player = new window.PandaPlayer(elId, {
        onReady: () => {
          if (cancelled) return;
          playerRef.current = player;

          player.onEvent((e) => {
            if (cancelled) return;
            const cur =
              typeof e.currentTime === "number" && isFinite(e.currentTime)
                ? e.currentTime
                : safeNum(player.getCurrentTime);
            const dur = safeNum(player.getDuration) || durationRef.current || 0;
            const pct = dur > 0 ? Math.min(100, (cur / dur) * 100) : 0;
            if (pct > maxPct) maxPct = pct;

            const emit = (concluida: boolean) =>
              onProgressRef.current?.({
                percentual: Math.round(maxPct * 10) / 10,
                posicaoSegundos: Math.max(0, Math.floor(cur)),
                concluida,
              });

            switch (e.message) {
              case "panda_timeupdate": {
                const now = Date.now();
                if (now - lastSent < PING_MS) return;
                lastSent = now;
                if (!concluded && maxPct >= CONCLUI_PCT) {
                  concluded = true;
                  emit(true);
                } else {
                  emit(false);
                }
                break;
              }
              case "panda_pause":
                lastSent = Date.now();
                emit(concluded);
                break;
              case "panda_ended":
                lastSent = Date.now();
                concluded = true;
                emit(true);
                break;
            }
          });
        },
      });
    };

    window.pandascripttag = window.pandascripttag || [];
    window.pandascripttag.push(init);

    return () => {
      cancelled = true;
      const p = playerRef.current;
      if (p) {
        // Flush final: registra a posição exata ao trocar de aula / sair.
        const cur = safeNum(p.getCurrentTime);
        if (cur > 0) {
          onProgressRef.current?.({
            percentual: Math.round(maxPct * 10) / 10,
            posicaoSegundos: Math.floor(cur),
            concluida: concluded,
          });
        }
        try {
          p.destroy?.();
        } catch {
          /* SDK pode não expor destroy; ignorar */
        }
      }
      playerRef.current = null;
    };
  }, [videoId]);

  if (!PANDA_BASE || !videoId) {
    return <Placeholder title={title} />;
  }

  const sep = PANDA_BASE.includes("?") ? "&" : "?";
  const params = new URLSearchParams({ v: videoId, controls: CONTROLS });
  if (startAt > 0) params.set("startTime", String(Math.floor(startAt)));
  // DRM: embed privado quando o backend assinou um token.
  if (playerToken) {
    params.set("watermark", playerToken);
    if (drmGroupId) params.set("drm_group_id", drmGroupId);
  }
  const src = `${PANDA_BASE}${sep}${params.toString()}`;

  return (
    <div className="video-stage" style={{ display: "block", padding: 0 }}>
      <iframe
        key={videoId}
        id={`panda-${videoId}`}
        src={src}
        title={title ?? "Aula"}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
        allowFullScreen
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          border: 0,
        }}
      />
    </div>
  );
}
