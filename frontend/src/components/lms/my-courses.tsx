"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { ApiError } from "@/lib/api";
import {
  cancelarMatricula,
  getMatriculas,
  type MatriculaItem,
} from "@/lib/auth-api";

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

function mensagemErro(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === "FORA_DO_PRAZO")
      return "O prazo de 7 dias para cancelamento já passou.";
    if (e.code === "RECURSO_CONSUMIDO" || e.code === "LIMITE_REEMBOLSOS")
      return e.message; // já vem explicando "fale com o suporte"
    if (e.code === "STRIPE_ERRO")
      return "Falha ao processar o reembolso — tente novamente em instantes.";
    return e.message;
  }
  return "Não foi possível cancelar. Tente novamente.";
}

const MOTIVO_HINT: Record<
  NonNullable<MatriculaItem["motivo_bloqueio"]>,
  string
> = {
  RECURSO_CONSUMIDO:
    "Você já avançou no conteúdo — para cancelar, fale com o suporte.",
  LIMITE_REEMBOLSOS:
    "Limite de cancelamentos automáticos atingido — novos pedidos passam pelo suporte.",
};

const ORIGEM_LABEL: Record<MatriculaItem["origem"], string> = {
  avulsa: "Compra avulsa",
  assinatura: "Assinatura",
  manual: "Matrícula manual",
};

export function MyCourses() {
  const router = useRouter();
  const qc = useQueryClient();
  const [aviso, setAviso] = useState<{
    tipo: "ok" | "erro";
    msg: string;
  } | null>(null);

  const matQ = useQuery({
    queryKey: ["me", "matriculas"],
    queryFn: getMatriculas,
  });
  const mats = matQ.data?.items ?? [];
  const vigentes = mats.filter((m) => m.status === "ativo");
  const passadas = mats.filter((m) => m.status !== "ativo");

  const cancelar = useMutation({
    mutationFn: (id: string) => cancelarMatricula(id),
    onSuccess: (r) => {
      setAviso({
        tipo: "ok",
        msg: r.assinatura_cancelada
          ? `Assinatura cancelada e reembolsada — ${r.cursos_revogados} curso(s) revogado(s).`
          : "Compra cancelada e reembolsada. O estorno aparece na fatura em alguns dias.",
      });
      qc.invalidateQueries({ queryKey: ["me", "matriculas"] });
      qc.invalidateQueries({ queryKey: ["me", "dashboard"] });
    },
    onError: (e) => setAviso({ tipo: "erro", msg: mensagemErro(e) }),
  });

  const confirmarCancelamento = (m: MatriculaItem) => {
    const aviso =
      m.origem === "assinatura"
        ? `Cancelar a ASSINATURA reembolsa o valor pago e revoga o acesso a TODOS os cursos dela.\n\n`
        : `Cancelar esta compra reembolsa o valor pago e encerra o acesso ao curso.\n\n`;
    if (
      window.confirm(
        `${aviso}Você está dentro do prazo de 7 dias (até ${m.cancelavel_ate ? fmtData(m.cancelavel_ate) : "—"}). Deseja continuar?`,
      )
    ) {
      cancelar.mutate(m.id);
    }
  };

  if (matQ.isLoading) {
    return (
      <div className="content">
        <span className="tag-mono muted">Carregando seus cursos…</span>
      </div>
    );
  }

  return (
    <div className="content blueprint" style={{ position: "relative" }}>
      <Reveal style={{ marginBottom: 26 }}>
        <div className="tag-mono amber" style={{ marginBottom: 8 }}>
          {"// MEUS CURSOS"}
        </div>
        <h1 style={{ fontSize: "2.1rem", marginBottom: 6 }}>Cursos vigentes</h1>
        <p className="muted">
          Acompanhe a vigência de cada acesso. Compras feitas há menos de 7 dias
          podem ser canceladas com reembolso integral.
        </p>
      </Reveal>

      {aviso && (
        <div
          className="flex center gap-3"
          style={{
            marginBottom: 20,
            padding: "12px 16px",
            borderRadius: 10,
            background:
              aviso.tipo === "ok"
                ? "rgba(34,197,94,0.1)"
                : "rgba(239,68,68,0.1)",
            border:
              aviso.tipo === "ok"
                ? "1px solid rgba(34,197,94,0.35)"
                : "1px solid rgba(239,68,68,0.35)",
          }}
        >
          <Icon
            name={aviso.tipo === "ok" ? "checkCircle" : "x"}
            size={18}
            style={{
              color: aviso.tipo === "ok" ? "var(--success)" : "var(--danger)",
              flexShrink: 0,
            }}
          />
          <span style={{ fontSize: "0.92rem" }}>{aviso.msg}</span>
        </div>
      )}

      {vigentes.length === 0 ? (
        <div className="card" style={{ padding: 28, textAlign: "center" }}>
          <p className="muted" style={{ marginBottom: 14 }}>
            Você não tem cursos vigentes no momento.
          </p>
          <Button
            variant="secondary"
            icon="book"
            onClick={() => router.push("/cursos")}
          >
            Ver catálogo
          </Button>
        </div>
      ) : (
        <Reveal
          stagger
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          {vigentes.map((m) => (
            <div key={m.id} className="card" style={{ padding: "18px 22px" }}>
              <div
                className="flex center gap-3"
                style={{ flexWrap: "wrap", marginBottom: 10 }}
              >
                <span style={{ fontWeight: 600, fontSize: "1.05rem", flex: 1 }}>
                  {m.curso.titulo}
                </span>
                <Badge variant={m.origem === "assinatura" ? "premium" : "cyan"}>
                  {ORIGEM_LABEL[m.origem]}
                </Badge>
                <Badge variant="success">ativo</Badge>
              </div>
              <div
                className="flex center gap-6"
                style={{ flexWrap: "wrap", marginBottom: 14 }}
              >
                <span className="tag-mono">
                  início {fmtData(m.data_inicio)} · expira{" "}
                  {fmtData(m.data_expiracao)}
                </span>
                <Badge variant={m.dias_restantes <= 15 ? "warning" : ""}>
                  {m.dias_restantes} dias restantes
                </Badge>
                <span className="tag-mono">
                  {Math.round(m.progresso_percentual)}% concluído
                </span>
              </div>
              <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
                <Button
                  variant="secondary"
                  size="sm"
                  icon="play"
                  onClick={() =>
                    router.push(
                      `/curso?slug=${encodeURIComponent(m.curso.slug)}`,
                    )
                  }
                >
                  Continuar curso
                </Button>
                {m.cancelavel && (
                  <Button
                    variant="ghost"
                    size="sm"
                    icon="x"
                    onClick={() => confirmarCancelamento(m)}
                    disabled={cancelar.isPending}
                  >
                    {cancelar.isPending
                      ? "Processando..."
                      : `Cancelar e reembolsar (até ${m.cancelavel_ate ? fmtData(m.cancelavel_ate) : "7 dias"})`}
                  </Button>
                )}
                {!m.cancelavel && m.motivo_bloqueio && (
                  <span
                    className="tag-mono subtle"
                    style={{ maxWidth: 360, lineHeight: 1.4 }}
                  >
                    {MOTIVO_HINT[m.motivo_bloqueio]}
                  </span>
                )}
              </div>
            </div>
          ))}
        </Reveal>
      )}

      {passadas.length > 0 && (
        <div style={{ marginTop: 36 }}>
          <h3 style={{ fontSize: "1.1rem", marginBottom: 12 }}>
            Acessos encerrados
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {passadas.map((m) => (
              <div
                key={m.id}
                className="flex center between card"
                style={{ padding: "12px 18px", opacity: 0.75 }}
              >
                <span style={{ fontSize: "0.95rem" }}>{m.curso.titulo}</span>
                <div className="flex center gap-3">
                  <Badge variant="warning">{m.status}</Badge>
                  <span className="tag-mono">
                    expirou {fmtData(m.data_expiracao)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
