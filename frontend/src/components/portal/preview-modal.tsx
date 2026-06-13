"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { getPreview, type AulaPreview } from "@/lib/api";
import { PandaPlayer } from "./panda-player";

/** Modal "Assistir aula grátis": carrega as aulas gratuitas do curso e toca. */
export function PreviewModal({
  slug,
  onClose,
}: {
  slug: string;
  onClose: () => void;
}) {
  const [aulas, setAulas] = useState<AulaPreview[] | null>(null);
  const [sel, setSel] = useState(0);

  useEffect(() => {
    getPreview(slug)
      .then(setAulas)
      .catch(() => setAulas([]));
  }, [slug]);

  const atual = aulas?.[sel];

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        background: "rgba(5,7,10,0.78)",
        backdropFilter: "blur(4px)",
        display: "grid",
        placeItems: "center",
        padding: 16,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 780, width: "100%", padding: 18 }}
      >
        <div
          className="flex center between"
          style={{ marginBottom: 12, gap: 12 }}
        >
          <span className="flex center gap-2" style={{ fontWeight: 600 }}>
            <Icon name="bolt" size={16} style={{ color: "var(--primary)" }} />
            Aula grátis
          </span>
          <button onClick={onClose} className="btn btn-ghost btn-sm" aria-label="Fechar">
            <Icon name="x" size={18} />
          </button>
        </div>

        {aulas === null ? (
          <span className="tag-mono muted">Carregando prévia…</span>
        ) : aulas.length === 0 ? (
          <span className="muted">Sem prévia disponível neste curso.</span>
        ) : (
          <>
            <PandaPlayer
              videoId={atual?.panda_video_id ?? null}
              title={atual?.titulo}
            />
            {aulas.length > 1 && (
              <div style={{ marginTop: 12, display: "grid", gap: 6 }}>
                {aulas.map((a, i) => (
                  <button
                    key={a.id}
                    onClick={() => setSel(i)}
                    className="flex center gap-2"
                    style={{
                      textAlign: "left",
                      padding: "9px 12px",
                      borderRadius: 8,
                      border: 0,
                      cursor: "pointer",
                      fontSize: "0.92rem",
                      background:
                        i === sel ? "var(--primary-soft)" : "var(--surface-2)",
                      color: i === sel ? "var(--primary)" : "var(--text)",
                    }}
                  >
                    <Icon name="play" size={13} />
                    {a.titulo}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
