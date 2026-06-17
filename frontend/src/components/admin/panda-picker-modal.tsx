"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import {
  listarPastasPanda,
  listarVideosPanda,
  type PandaPasta,
  type PandaVideoItem,
} from "@/lib/admin-api";

function fmt(seg: number | null): string {
  if (!seg) return "—";
  const m = Math.floor(seg / 60);
  const s = seg % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Seletor da biblioteca do Panda: escolhe um vídeo já existente (busca + pasta).
 * Selecionar chama onSelect com o item (id + duração) e fecha. */
export function PandaPickerModal({
  onSelect,
  onClose,
}: {
  onSelect: (v: PandaVideoItem) => void;
  onClose: () => void;
}) {
  const [pastas, setPastas] = useState<PandaPasta[]>([]);
  const [pastaId, setPastaId] = useState("");
  const [busca, setBusca] = useState("");
  const [itens, setItens] = useState<PandaVideoItem[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  // Pastas (uma vez). Falha silenciosa: o filtro some, mas a lista ainda funciona.
  useEffect(() => {
    let alive = true;
    listarPastasPanda()
      .then((d) => alive && setPastas(d.itens))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  // Lista da biblioteca, refeita a cada mudança de busca (debounce) / pasta.
  useEffect(() => {
    let alive = true;
    setItens(null);
    setErro(null);
    const t = setTimeout(() => {
      listarVideosPanda({
        title: busca.trim() || undefined,
        folder_id: pastaId || undefined,
        limit: 40,
      })
        .then((d) => alive && setItens(d.itens))
        .catch(
          (e) =>
            alive &&
            setErro(e?.message ?? "Falha ao carregar a biblioteca do Panda."),
        );
    }, 400);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [busca, pastaId]);

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
          width: "min(880px, 100%)",
          maxHeight: "86vh",
          padding: 20,
          display: "grid",
          gap: 14,
          gridTemplateRows: "auto auto 1fr",
        }}
      >
        <div className="flex center between">
          <h3 style={{ fontSize: "1.05rem" }}>Selecionar vídeo do Panda</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            <Icon name="x" size={16} />
          </button>
        </div>

        <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
          <input
            className="input"
            placeholder="Buscar por título…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          {pastas.length > 0 && (
            <select
              className="input"
              value={pastaId}
              onChange={(e) => setPastaId(e.target.value)}
              style={{ maxWidth: 240 }}
            >
              <option value="">Todas as pastas</option>
              {pastas.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome}
                </option>
              ))}
            </select>
          )}
        </div>

        <div style={{ overflowY: "auto", minHeight: 120 }}>
          {erro ? (
            <span className="muted" style={{ fontSize: "0.92rem" }}>
              {erro}
            </span>
          ) : itens === null ? (
            <span className="tag-mono muted">Carregando biblioteca…</span>
          ) : itens.length === 0 ? (
            <span className="muted" style={{ fontSize: "0.92rem" }}>
              Nenhum vídeo encontrado na conta do Panda
              {busca.trim() ? ` para “${busca.trim()}”.` : "."}
            </span>
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                gap: 12,
              }}
            >
              {itens.map((v) => (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => {
                    onSelect(v);
                    onClose();
                  }}
                  className="card"
                  style={{
                    padding: 0,
                    textAlign: "left",
                    cursor: "pointer",
                    overflow: "hidden",
                    display: "grid",
                    gridTemplateRows: "auto auto",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div
                    style={{
                      aspectRatio: "16 / 9",
                      background: "var(--surface-2, #0c0f16)",
                      backgroundImage: v.thumbnail
                        ? `url(${v.thumbnail})`
                        : undefined,
                      backgroundSize: "cover",
                      backgroundPosition: "center",
                      display: "grid",
                      placeItems: "center",
                      position: "relative",
                    }}
                  >
                    {!v.thumbnail && <Icon name="play" size={26} />}
                    <span
                      className="tag-mono"
                      style={{
                        position: "absolute",
                        right: 6,
                        bottom: 6,
                        background: "rgba(4,6,10,0.78)",
                        padding: "1px 6px",
                        borderRadius: 4,
                      }}
                    >
                      {fmt(v.duracao_segundos)}
                    </span>
                  </div>
                  <div style={{ padding: "8px 10px", display: "grid", gap: 2 }}>
                    <span
                      style={{
                        fontSize: "0.9rem",
                        fontWeight: 600,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={v.titulo}
                    >
                      {v.titulo}
                    </span>
                    {v.status && v.status !== "CONVERTED" && (
                      <span className="tag-mono muted">{v.status}</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
