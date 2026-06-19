"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApiError } from "@/lib/api";
import {
  ADMIN_CRUD,
  bloquearAluno,
  cancelarMatriculaAdmin,
  listarMatriculasReembolso,
  type AdminRow,
  type MatriculaAdmin,
  type MatriculaFiltro,
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

function initials(nome: string): string {
  return (nome || "?")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

const ORIGEM_LABEL: Record<MatriculaAdmin["origem"], string> = {
  avulsa: "Avulsa",
  assinatura: "Assinatura",
  manual: "Manual",
};

const STATUS_SEG: { key: NonNullable<MatriculaFiltro["status"]>; label: string }[] =
  [
    { key: "ativo", label: "Ativos" },
    { key: "inativo", label: "Inativos" },
    { key: "bloqueado", label: "Bloqueados" },
  ];

const ORIGEM_OPTS: { key: "" | MatriculaAdmin["origem"]; label: string }[] = [
  { key: "", label: "Plano e cursos (todos)" },
  { key: "assinatura", label: "Plano (assinatura)" },
  { key: "avulsa", label: "Curso avulso" },
  { key: "manual", label: "Matrícula manual" },
];

/** Gestão de matrículas: lista aluno × curso/plano com filtros (default ativos),
 * com ações de bloquear acesso e cancelar/estornar — sem trava de 7 dias (cortesia
 * a critério do suporte). */
export function AdminRefunds({ onToast }: { onToast: (msg: string) => void }) {
  const qc = useQueryClient();
  const [status, setStatus] =
    useState<NonNullable<MatriculaFiltro["status"]>>("ativo");
  const [origem, setOrigem] = useState<"" | MatriculaAdmin["origem"]>("");
  const [cursoId, setCursoId] = useState("");
  const [busca, setBusca] = useState("");
  const [acao, setAcao] = useState<string | null>(null); // matricula_id em ação

  const filtro: MatriculaFiltro = {
    status,
    ...(origem ? { origem } : {}),
    ...(cursoId ? { curso_id: cursoId } : {}),
  };

  const { data: cursos } = useQuery({
    queryKey: ["admin", "courses"],
    queryFn: ADMIN_CRUD.courses.list,
  });

  const queryKey = ["admin", "matriculas", filtro];
  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: () => listarMatriculasReembolso(filtro),
  });

  const linhas = useMemo(() => {
    const all = (data ?? []) as MatriculaAdmin[];
    const q = busca.trim().toLowerCase();
    if (!q) return all;
    return all.filter((m) =>
      `${m.aluno_nome} ${m.aluno_email} ${m.curso_titulo}`
        .toLowerCase()
        .includes(q),
    );
  }, [data, busca]);

  const recarregar = () =>
    qc.invalidateQueries({ queryKey: ["admin", "matriculas"] });

  const alternarBloqueio = async (m: MatriculaAdmin) => {
    const bloquear = !m.aluno_bloqueado;
    const msg = bloquear
      ? `Bloquear o acesso de ${m.aluno_nome}? O aluno não conseguirá entrar até ser liberado (sessões ativas caem na hora).`
      : `Liberar o acesso de ${m.aluno_nome}?`;
    if (!window.confirm(msg)) return;
    setAcao(m.matricula_id);
    try {
      await bloquearAluno(m.aluno_id, bloquear);
      onToast(bloquear ? "Acesso bloqueado." : "Acesso liberado.");
      await recarregar();
    } catch (e) {
      onToast(
        e instanceof ApiError ? e.message : "Não foi possível alterar o acesso.",
      );
    } finally {
      setAcao(null);
    }
  };

  const cancelar = async (m: MatriculaAdmin) => {
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
    setAcao(m.matricula_id);
    try {
      const r = await cancelarMatriculaAdmin(m.matricula_id);
      onToast(
        r.assinatura_cancelada
          ? `Assinatura cancelada e reembolsada (${r.cursos_revogados} curso(s) revogado(s)).`
          : "Compra cancelada e reembolsada.",
      );
      await recarregar();
    } catch (e) {
      onToast(
        e instanceof ApiError ? e.message : "Não foi possível cancelar.",
      );
    } finally {
      setAcao(null);
    }
  };

  return (
    <div className="content blueprint" style={{ maxWidth: 1100, position: "relative" }}>
      <div style={{ marginBottom: 18 }}>
        <p className="muted" style={{ maxWidth: 680 }}>
          Gestão de acesso e reembolso por matrícula (aluno × curso/plano). Bloqueie
          o acesso ou cancele compras com estorno via Stripe. A janela de 7 dias é o
          direito do aluno; aqui não há trava de prazo (cortesia do suporte).
        </p>
      </div>

      {/* filtros */}
      <div className="toolbar" style={{ marginBottom: 18 }}>
        <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
          <div className="search">
            <Icon name="gauge" size={16} />
            <input
              placeholder="Buscar aluno, e-mail ou curso..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          </div>
          <div className="seg">
            {STATUS_SEG.map((s) => (
              <button
                key={s.key}
                className={status === s.key ? "active" : ""}
                onClick={() => setStatus(s.key)}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
          <select
            className="input"
            style={{ width: "auto" }}
            value={origem}
            onChange={(e) =>
              setOrigem(e.target.value as "" | MatriculaAdmin["origem"])
            }
          >
            {ORIGEM_OPTS.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label}
              </option>
            ))}
          </select>
          <select
            className="input"
            style={{ width: "auto" }}
            value={cursoId}
            onChange={(e) => setCursoId(e.target.value)}
          >
            <option value="">Todos os cursos</option>
            {((cursos ?? []) as AdminRow[]).map((c) => (
              <option key={c.id} value={c.id}>
                {String(c.titulo)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && (
        <span className="tag-mono muted">Carregando matrículas…</span>
      )}
      {isError && (
        <span className="tag-mono" style={{ color: "var(--danger)" }}>
          Falha ao carregar. Sua sessão pode ter expirado — saia e entre de novo.
        </span>
      )}

      {!isLoading && !isError && linhas.length === 0 && (
        <div className="card" style={{ padding: 22 }}>
          <span className="muted">Nenhuma matrícula com esses filtros.</span>
        </div>
      )}

      {linhas.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {linhas.map((m) => (
            <div key={m.matricula_id} className="card" style={{ padding: "14px 18px" }}>
              <div className="flex center gap-3" style={{ flexWrap: "wrap" }}>
                <span className="cell-avatar">{initials(m.aluno_nome)}</span>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontWeight: 600 }}>{m.aluno_nome}</div>
                  <span className="tag-mono">{m.aluno_email}</span>
                </div>
                <span style={{ fontWeight: 600, minWidth: 160 }}>
                  {m.curso_titulo}
                </span>
                <Badge variant={m.origem === "assinatura" ? "premium" : "cyan"}>
                  {ORIGEM_LABEL[m.origem]}
                </Badge>
                {m.aluno_bloqueado ? (
                  <Badge variant="warning">bloqueado</Badge>
                ) : (
                  <Badge variant={m.status === "ativo" ? "success" : ""}>
                    {m.status}
                  </Badge>
                )}
              </div>
              <div
                className="flex center gap-6"
                style={{ flexWrap: "wrap", marginTop: 10 }}
              >
                <span className="tag-mono">
                  pago em {fmtData(m.pago_em)} · {fmtValor(m.valor)}
                </span>
                {m.cancelavel && (
                  <Badge variant={m.dentro_da_janela ? "success" : "warning"}>
                    {m.dentro_da_janela ? "dentro dos 7 dias" : "fora dos 7 dias"}
                  </Badge>
                )}
                <div className="flex center gap-3" style={{ marginLeft: "auto" }}>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon="lock"
                    onClick={() => alternarBloqueio(m)}
                    disabled={acao !== null}
                  >
                    {m.aluno_bloqueado ? "Desbloquear" : "Bloquear"}
                  </Button>
                  {m.cancelavel ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      icon="x"
                      onClick={() => cancelar(m)}
                      disabled={acao !== null}
                    >
                      {acao === m.matricula_id
                        ? "Processando..."
                        : "Cancelar e reembolsar"}
                    </Button>
                  ) : (
                    <span className="tag-mono subtle">sem estorno</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
