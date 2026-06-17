"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { retencaoAula, type RetencaoInfo } from "@/lib/admin-api";

function fmt(seg: number): string {
  const m = Math.floor(seg / 60);
  const s = seg % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

// Reduz a série a no máximo `max` barras (vídeos longos têm 1 ponto a cada 5s).
function amostrar<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr;
  const passo = Math.ceil(arr.length / max);
  return arr.filter((_, i) => i % passo === 0);
}

export function RetencaoModal({
  aulaId,
  titulo,
  onClose,
}: {
  aulaId: string;
  titulo: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<RetencaoInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    retencaoAula(aulaId)
      .then((d) => alive && setData(d))
      .catch(
        (e) => alive && setErr(e?.message ?? "Falha ao carregar a retenção."),
      );
    return () => {
      alive = false;
    };
  }, [aulaId]);

  const pts = data?.pontos ?? [];
  const media = pts.length
    ? Math.round(pts.reduce((a, p) => a + p.percentual, 0) / pts.length)
    : 0;
  let quedaSeg = 0;
  let quedaVal = 0;
  for (let i = 1; i < pts.length; i++) {
    const d = pts[i - 1].percentual - pts[i].percentual;
    if (d > quedaVal) {
      quedaVal = d;
      quedaSeg = pts[i].segundo;
    }
  }
  const barras = amostrar(pts, 80);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4,6,10,0.72)",
        display: "grid",
        placeItems: "center",
        zIndex: 60,
        padding: 16,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(720px, 100%)",
          padding: 20,
          display: "grid",
          gap: 14,
        }}
      >
        <div className="flex center between">
          <h3 style={{ fontSize: "1.05rem" }}>Retenção · {titulo}</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            <Icon name="x" size={16} />
          </button>
        </div>

        {err ? (
          <span className="muted" style={{ fontSize: "0.92rem" }}>
            {err}
          </span>
        ) : !data ? (
          <span className="tag-mono muted">Carregando retenção…</span>
        ) : pts.length === 0 ? (
          <span className="muted" style={{ fontSize: "0.92rem" }}>
            Sem dados de retenção ainda (vídeo novo ou ainda sem visualizações).
          </span>
        ) : (
          <>
            <div className="flex center gap-6" style={{ flexWrap: "wrap" }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: "1.4rem" }}>
                  {media}%
                </div>
                <span className="tag-mono">retenção média</span>
              </div>
              {quedaVal > 0 && (
                <div>
                  <div style={{ fontWeight: 700, fontSize: "1.4rem" }}>
                    {fmt(quedaSeg)}
                  </div>
                  <span className="tag-mono">
                    maior queda (−{Math.round(quedaVal)}%)
                  </span>
                </div>
              )}
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: 2,
                height: 160,
                padding: "8px 0",
                borderBottom: "1px solid var(--border)",
              }}
            >
              {barras.map((p) => (
                <div
                  key={p.segundo}
                  title={`${fmt(p.segundo)} · ${Math.round(p.percentual)}%`}
                  style={{
                    flex: 1,
                    height: `${Math.max(2, Math.min(100, p.percentual))}%`,
                    background: "var(--primary)",
                    opacity: 0.35 + (p.percentual / 100) * 0.65,
                    borderRadius: "2px 2px 0 0",
                  }}
                />
              ))}
            </div>
            <div className="flex center between">
              <span className="tag-mono">0:00</span>
              <span className="tag-mono">
                {fmt(pts[pts.length - 1]?.segundo ?? 0)}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
