"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApiError } from "@/lib/api";
import {
  buscarReembolsos,
  cancelarMatriculaAdmin,
  type AlunoReembolsos,
  type ReembolsoItem,
} from "@/lib/admin-api";

function fmtData(iso: string | null): string {
  if (!iso) return "—";
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

function fmtValor(v: number | null): string {
  if (v == null) return "—";
  return `R$ ${v.toFixed(2).replace(".", ",")}`;
}

const ORIGEM_LABEL: Record<ReembolsoItem["origem"], string> = {
  avulsa: "Avulsa",
  assinatura: "Assinatura",
  manual: "Manual",
};

/** Reembolsos pelo suporte: busca o aluno por e-mail e cancela/estorna compras.
 * Sem trava de 7 dias — a janela é o direito do ALUNO; aqui é decisão do suporte. */
export function AdminRefunds({ onToast }: { onToast: (msg: string) => void }) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [cancelando, setCancelando] = useState<string | null>(null);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState<AlunoReembolsos | null>(null);

  const buscar = async () => {
    if (busy || !email.trim()) return;
    setBusy(true);
    setErro("");
    try {
      setResultado(await buscarReembolsos(email.trim()));
    } catch (e) {
      setResultado(null);
      setErro(
        e instanceof ApiError && e.code === "ALUNO_NAO_ENCONTRADO"
          ? "Nenhum aluno com esse e-mail."
          : "Não foi possível buscar. Confira o e-mail e tente de novo.",
      );
    } finally {
      setBusy(false);
    }
  };

  const cancelar = async (m: ReembolsoItem) => {
    const partes = [
      m.origem === "assinatura"
        ? "Cancelar a ASSINATURA: reembolsa o último pagamento, cancela a recorrência na Stripe e revoga TODOS os cursos dela."
        : "Cancelar a compra: reembolsa o valor pago e encerra o acesso ao curso.",
      m.dentro_da_janela
        ? "O aluno está dentro da janela de 7 dias."
        : "ATENÇÃO: fora da janela de 7 dias — reembolso de cortesia.",
      `Valor a estornar: ${fmtValor(m.valor)}.`,
    ];
    if (!window.confirm(`${partes.join("\n\n")}\n\nConfirmar?`)) return;
    setCancelando(m.matricula_id);
    try {
      const r = await cancelarMatriculaAdmin(m.matricula_id);
      onToast(
        r.assinatura_cancelada
          ? `Assinatura cancelada e reembolsada (${r.cursos_revogados} curso(s) revogado(s)).`
          : "Compra cancelada e reembolsada.",
      );
      await buscar(); // recarrega a lista
    } catch (e) {
      onToast(
        e instanceof ApiError
          ? e.message
          : "Não foi possível cancelar — tente novamente.",
      );
    } finally {
      setCancelando(null);
    }
  };

  return (
    <div
      className="content blueprint"
      style={{ maxWidth: 980, position: "relative" }}
    >
      <div style={{ marginBottom: 22 }}>
        <p className="muted" style={{ maxWidth: 640 }}>
          Busque o aluno pelo e-mail para cancelar compras e estornar pagamentos
          via Stripe. Dentro de 7 dias o próprio aluno consegue cancelar pela
          área dele; aqui não há trava de prazo (cortesia a critério do
          suporte).
        </p>
      </div>

      <form
        className="flex center gap-3"
        style={{ marginBottom: 24, maxWidth: 560 }}
        onSubmit={(e) => {
          e.preventDefault();
          buscar();
        }}
      >
        <div className="input-group" style={{ flex: 1 }}>
          <span className="ico">
            <Icon name="message" size={17} />
          </span>
          <input
            className="input"
            type="email"
            placeholder="email do aluno"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <Button type="submit" variant="primary" icon="arrow" disabled={busy}>
          {busy ? "Buscando..." : "Buscar"}
        </Button>
      </form>

      {erro && (
        <div
          className="flex center gap-3"
          style={{
            marginBottom: 18,
            padding: "12px 14px",
            borderRadius: 10,
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.35)",
            maxWidth: 560,
          }}
        >
          <Icon
            name="x"
            size={18}
            style={{ color: "var(--danger)", flexShrink: 0 }}
          />
          <span style={{ fontSize: "0.9rem" }}>{erro}</span>
        </div>
      )}

      {resultado && (
        <div>
          <div className="flex center gap-3" style={{ marginBottom: 16 }}>
            <span className="avatar">
              {resultado.nome
                .split(" ")
                .map((n) => n[0])
                .slice(0, 2)
                .join("")
                .toUpperCase()}
            </span>
            <div>
              <div style={{ fontWeight: 600 }}>{resultado.nome}</div>
              <span className="tag-mono">{resultado.email}</span>
            </div>
          </div>

          {resultado.matriculas.length === 0 ? (
            <div className="card" style={{ padding: 22 }}>
              <span className="muted">Este aluno não tem matrículas.</span>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {resultado.matriculas.map((m) => (
                <div
                  key={m.matricula_id}
                  className="card"
                  style={{ padding: "14px 18px" }}
                >
                  <div
                    className="flex center gap-3"
                    style={{ flexWrap: "wrap" }}
                  >
                    <span style={{ fontWeight: 600, flex: 1, minWidth: 200 }}>
                      {m.curso_titulo}
                    </span>
                    <Badge
                      variant={m.origem === "assinatura" ? "premium" : "cyan"}
                    >
                      {ORIGEM_LABEL[m.origem]}
                    </Badge>
                    <Badge
                      variant={m.status === "ativo" ? "success" : "warning"}
                    >
                      {m.status}
                    </Badge>
                  </div>
                  <div
                    className="flex center gap-6"
                    style={{ flexWrap: "wrap", marginTop: 10 }}
                  >
                    <span className="tag-mono">
                      pago em {fmtData(m.pago_em)} · {fmtValor(m.valor)}
                    </span>
                    {m.cancelavel && (
                      <Badge
                        variant={m.dentro_da_janela ? "success" : "warning"}
                      >
                        {m.dentro_da_janela
                          ? "dentro dos 7 dias"
                          : "fora dos 7 dias"}
                      </Badge>
                    )}
                    {m.cancelavel ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        icon="x"
                        onClick={() => cancelar(m)}
                        disabled={cancelando !== null}
                      >
                        {cancelando === m.matricula_id
                          ? "Processando..."
                          : "Cancelar e reembolsar"}
                      </Button>
                    ) : (
                      <span className="tag-mono subtle">
                        sem pagamento reembolsável
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
