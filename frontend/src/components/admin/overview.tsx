"use client";

import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { AdminItem, EntityKey } from "@/lib/admin-data";
import { ADMIN_CRUD } from "@/lib/admin-api";

function StatCard({
  icon,
  value,
  label,
  accent,
  hint,
}: {
  icon: string;
  value: number;
  label: string;
  accent?: string;
  hint?: string;
}) {
  return (
    <div className="kpi">
      <div className="kpi-label">
        <Icon
          name={icon}
          size={15}
          style={{ color: accent || "var(--primary)" }}
        />
        {label}
      </div>
      <div className="kpi-value" style={{ color: accent || "var(--text)" }}>
        {value}
      </div>
      {hint && (
        <span className="kpi-delta flat" style={{ marginTop: 10 }}>
          {hint}
        </span>
      )}
    </div>
  );
}

// Mesma queryKey do RemoteEntityManager → cache compartilhado e atualizado
// automaticamente quando um cadastro é criado/editado/excluído.
function useAdminList(key: EntityKey): AdminItem[] {
  const { data } = useQuery({
    queryKey: ["admin", key],
    queryFn: ADMIN_CRUD[key].list,
  });
  return (data ?? []) as AdminItem[];
}

function initials(name: string) {
  return (name || "?")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Overview({
  onNav,
  onNew,
}: {
  onNav: (v: string) => void;
  onNew: (key: EntityKey) => void;
}) {
  const students = useAdminList("students");
  const courses = useAdminList("courses");
  const testimonials = useAdminList("testimonials");
  const packages = useAdminList("packages");

  const activeStudents = students.filter((s) => s.status === "Ativo").length;
  const pending = testimonials.filter((t) => t.status === "Pendente");
  const activePkgs = packages.filter((p) => p.status === "Ativo").length;

  return (
    <div
      className="content blueprint"
      style={{ maxWidth: 1180, position: "relative" }}
    >
      <div style={{ marginBottom: 26 }}>
        <div className="tag-mono amber" style={{ marginBottom: 8 }}>
          // PAINEL ADMINISTRADOR
        </div>
        <h1 style={{ fontSize: "2rem", marginBottom: 6 }}>Visão geral</h1>
        <p className="muted">
          Gestão de alunos, cursos, depoimentos e pacotes da Rödelcar.
        </p>
      </div>

      <div className="stat-strip">
        <StatCard
          icon="users"
          value={activeStudents}
          label="Alunos ativos"
          hint={`${students.length} no total`}
        />
        <StatCard
          icon="book"
          value={courses.length}
          label="Cursos"
          hint="no catálogo"
        />
        <StatCard
          icon="message"
          value={pending.length}
          label="Depoimentos pendentes"
          accent={pending.length ? "var(--warning)" : "var(--success)"}
          hint="aguardando aprovação"
        />
        <StatCard
          icon="award"
          value={activePkgs}
          label="Pacotes ativos"
          hint="à venda no site"
        />
      </div>

      <div
        className="admin-overview-grid"
        style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}
      >
        {/* recent students */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div
            className="flex center between"
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <h3 style={{ fontSize: "1.05rem" }}>Alunos recentes</h3>
            <Button
              variant="link"
              iconRight="arrow"
              onClick={() => onNav("students")}
            >
              Gerenciar
            </Button>
          </div>
          <div>
            {students.length === 0 && (
              <div
                className="muted"
                style={{ padding: "22px 20px", fontSize: "0.92rem" }}
              >
                Nenhum aluno cadastrado ainda.
              </div>
            )}
            {students.slice(0, 5).map((s, i) => (
              <div
                key={String(s.id)}
                className="flex center between"
                style={{
                  padding: "13px 20px",
                  borderTop: i ? "1px solid var(--border)" : "none",
                }}
              >
                <div className="cell-user">
                  <span className="cell-avatar">
                    {initials(String(s.nome))}
                  </span>
                  <div>
                    <div
                      className="cell-strong"
                      style={{ fontSize: "0.92rem" }}
                    >
                      {s.nome}
                    </div>
                    <div className="tag-mono">{s.email}</div>
                  </div>
                </div>
                <div className="flex center gap-3">
                  <Badge variant="">{Number(s.matriculas) || 0} cursos</Badge>
                  <Badge variant={s.status === "Ativo" ? "success" : ""}>
                    {String(s.status)}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* pending approval / quick action */}
        <div style={{ display: "grid", gap: 20, alignContent: "start" }}>
          <div
            className="card blueprint"
            style={{ padding: 22, position: "relative", overflow: "hidden" }}
          >
            <div
              className="glow-amber"
              style={{ width: 240, height: 160, top: -70, right: -40 }}
            />
            <div style={{ position: "relative", zIndex: 1 }}>
              <Badge variant="warning" icon="message">
                {pending.length} para aprovar
              </Badge>
              <h3 style={{ fontSize: "1.15rem", margin: "12px 0 6px" }}>
                Depoimentos pendentes
              </h3>
              <p
                className="muted"
                style={{ fontSize: "0.92rem", marginBottom: 16 }}
              >
                {pending.length
                  ? `${pending[0].nome} e outros aguardam moderação para aparecer no site.`
                  : "Tudo aprovado. Nenhum depoimento na fila."}
              </p>
              <Button
                variant="secondary"
                block
                iconRight="arrow"
                onClick={() => onNav("testimonials")}
              >
                Revisar depoimentos
              </Button>
            </div>
          </div>
          {/* ação âmbar dominante */}
          <div className="card" style={{ padding: 22 }}>
            <h3 style={{ fontSize: "1.05rem", marginBottom: 6 }}>
              Cadastro rápido
            </h3>
            <p
              className="muted"
              style={{ fontSize: "0.9rem", marginBottom: 16 }}
            >
              Adicione um novo aluno ao portal.
            </p>
            <Button
              variant="primary"
              block
              icon="spark"
              onClick={() => onNew("students")}
            >
              Novo aluno
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
