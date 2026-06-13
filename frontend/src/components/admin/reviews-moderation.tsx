"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Stars } from "@/components/ui/stars";
import {
  buscarAvaliacoes,
  excluirAvaliacao,
  moderarAvaliacao,
  type AvaliacaoAdmin,
} from "@/lib/admin-api";

function fmtData(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/** Moderação das avaliações dos alunos: ocultar (Pendente) ou excluir.
 *  Comprador verificado publica direto; aqui o suporte retira o que for abusivo. */
export function AdminReviews({ onToast }: { onToast: (msg: string) => void }) {
  const [itens, setItens] = useState<AvaliacaoAdmin[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const carregar = async () => {
    try {
      setItens(await buscarAvaliacoes());
    } catch {
      onToast("Não foi possível carregar as avaliações.");
    }
  };

  useEffect(() => {
    carregar();
  }, []);

  const alternar = async (a: AvaliacaoAdmin) => {
    const novo = a.status === "Aprovado" ? "Pendente" : "Aprovado";
    setBusy(a.id);
    try {
      await moderarAvaliacao(a.id, novo);
      onToast(
        novo === "Pendente"
          ? "Avaliação ocultada do site."
          : "Avaliação aprovada e publicada.",
      );
      await carregar();
    } catch {
      onToast("Não foi possível atualizar.");
    } finally {
      setBusy(null);
    }
  };

  const excluir = async (a: AvaliacaoAdmin) => {
    if (!window.confirm("Excluir esta avaliação em definitivo?")) return;
    setBusy(a.id);
    try {
      await excluirAvaliacao(a.id);
      onToast("Avaliação excluída.");
      await carregar();
    } catch {
      onToast("Não foi possível excluir.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div
      className="content blueprint"
      style={{ maxWidth: 980, position: "relative" }}
    >
      <p className="muted" style={{ maxWidth: 640, marginBottom: 22 }}>
        Avaliações dos alunos (compradores verificados). Elas publicam direto;
        use <strong>Ocultar</strong> para tirar uma do site sem apagar, ou{" "}
        <strong>Excluir</strong> para remover de vez.
      </p>

      {itens === null ? (
        <span className="tag-mono muted">Carregando avaliações…</span>
      ) : itens.length === 0 ? (
        <div className="card" style={{ padding: 22 }}>
          <span className="muted">Nenhuma avaliação ainda.</span>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {itens.map((a) => (
            <div key={a.id} className="card" style={{ padding: "14px 18px" }}>
              <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
                <span style={{ fontWeight: 600, flex: 1, minWidth: 200 }}>
                  {a.curso_titulo}
                </span>
                <Stars value={a.nota} size={14} />
                <Badge
                  variant={a.status === "Aprovado" ? "success" : "warning"}
                >
                  {a.status === "Aprovado" ? "publicada" : "oculta"}
                </Badge>
              </div>
              {a.texto && (
                <p
                  className="muted"
                  style={{
                    fontSize: "0.92rem",
                    lineHeight: 1.5,
                    margin: "8px 0 0",
                  }}
                >
                  “{a.texto}”
                </p>
              )}
              <div
                className="flex center gap-3"
                style={{ flexWrap: "wrap", marginTop: 10 }}
              >
                <span className="tag-mono subtle">
                  {a.aluno_nome} · {fmtData(a.criado_em)}
                </span>
                <div style={{ flex: 1 }} />
                <Button
                  variant="ghost"
                  size="sm"
                  icon={a.status === "Aprovado" ? "lock" : "check"}
                  onClick={() => alternar(a)}
                  disabled={busy !== null}
                >
                  {a.status === "Aprovado" ? "Ocultar" : "Aprovar"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  icon="x"
                  onClick={() => excluir(a)}
                  disabled={busy !== null}
                >
                  Excluir
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
