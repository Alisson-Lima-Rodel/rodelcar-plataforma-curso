"use client";

import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/ui/icon";
import type { AdminItem, EntityKey } from "@/lib/admin-data";
import { ADMIN_CRUD, metricasDiarias } from "@/lib/admin-api";
import { MetricsChart } from "./metrics-chart";

function StatCard({
  icon,
  value,
  label,
  accent,
  hint,
  onClick,
}: {
  icon: string;
  value: number;
  label: string;
  accent?: string;
  hint?: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className="kpi kpi-clickable"
      onClick={onClick}
      style={{
        textAlign: "left",
        width: "100%",
        cursor: onClick ? "pointer" : "default",
        font: "inherit",
        color: "inherit",
        transition: "border-color 140ms, transform 140ms",
      }}
    >
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
    </button>
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

export function Overview({
  onNav,
}: {
  onNav: (v: string) => void;
  // onNew é passado pelo container, mas a visão geral não usa mais (removido o
  // bloco "Cadastro rápido"). Mantido opcional p/ não quebrar a chamada.
  onNew?: (key: EntityKey) => void;
}) {
  const students = useAdminList("students");
  const courses = useAdminList("courses");
  const testimonials = useAdminList("testimonials");
  const plans = useAdminList("plans");

  const activeStudents = students.filter((s) => s.status === "Ativo").length;
  const pending = testimonials.filter((t) => t.status === "Pendente");
  const activePlans = plans.filter((p) => p.status === "Ativo").length;

  const { data: metricas } = useQuery({
    queryKey: ["admin", "metricas", 90],
    queryFn: () => metricasDiarias(90),
  });

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
          Gestão de alunos, cursos, depoimentos e planos da Rödelcar.
        </p>
      </div>

      <div className="stat-strip">
        <StatCard
          icon="users"
          value={activeStudents}
          label="Alunos ativos"
          hint={`${students.length} no total · gerenciar`}
          onClick={() => onNav("students")}
        />
        <StatCard
          icon="book"
          value={courses.length}
          label="Cursos"
          hint="no catálogo · gerenciar"
          onClick={() => onNav("courses")}
        />
        <StatCard
          icon="message"
          value={pending.length}
          label="Depoimentos pendentes"
          accent={pending.length ? "var(--warning)" : "var(--success)"}
          hint="revisar depoimentos"
          onClick={() => onNav("testimonials")}
        />
        <StatCard
          icon="infinity"
          value={activePlans}
          label="Planos ativos"
          hint="à venda · gerenciar"
          onClick={() => onNav("plans")}
        />
      </div>

      <div style={{ marginTop: 22 }}>
        <MetricsChart data={metricas ?? []} />
      </div>
    </div>
  );
}
