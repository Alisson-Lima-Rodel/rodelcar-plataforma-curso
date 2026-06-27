"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Logo } from "@/components/ui/logo";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/badge";
import { getMatriculas, type Me } from "@/lib/auth-api";
import { activeLmsId, lmsHref } from "@/lib/lms-nav";
import { initialsOf } from "./lms-shell";

function fmtShort(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

const ITEMS: { id: string; label: string; icon: string }[] = [
  { id: "dashboard", label: "Painel", icon: "gauge" },
  { id: "player", label: "Continuar curso", icon: "play" },
  { id: "courses", label: "Meus cursos", icon: "book" },
  { id: "catalog", label: "Explorar cursos", icon: "spark" },
  { id: "certificate", label: "Certificados", icon: "award" },
  { id: "community", label: "Comunidade", icon: "users" },
];

export function Sidebar({
  aluno,
  onNavigate,
}: {
  aluno: Me;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active = activeLmsId(pathname);

  const matQ = useQuery({
    queryKey: ["me", "matriculas"],
    queryFn: getMatriculas,
  });
  const ativas = (matQ.data?.items ?? []).filter((m) => m.status === "ativo");
  // vigência exibida = a que expira primeiro
  const proxima = ativas.length
    ? ativas.reduce((a, b) => (a.dias_restantes <= b.dias_restantes ? a : b))
    : null;

  return (
    <aside className="sidebar">
      <Link
        href="/"
        style={{ padding: "4px 10px 22px", display: "inline-block" }}
        aria-label="Início"
        onClick={onNavigate}
      >
        <Logo size="md" tagline={false} />
      </Link>

      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {ITEMS.map((it) => (
          <Link
            key={it.id}
            href={lmsHref(it.id)}
            className={`nav-item ${active === it.id ? "active" : ""}`.trim()}
            onClick={onNavigate}
          >
            <Icon name={it.icon} size={19} />
            {it.label}
          </Link>
        ))}
      </nav>

      <div
        style={{
          marginTop: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        {/* vigência mini (matrícula que expira primeiro) */}
        {proxima && (
          <div
            style={{
              padding: 14,
              borderRadius: 12,
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="flex center between" style={{ marginBottom: 8 }}>
              <span className="tag-mono">VIGÊNCIA</span>
              <Badge
                variant={proxima.dias_restantes <= 15 ? "warning" : "cyan"}
              >
                {proxima.dias_restantes} dias
              </Badge>
            </div>
            <div className="progress" style={{ marginBottom: 8 }}>
              <span
                style={{
                  width: `${Math.min(100, Math.round((proxima.dias_restantes / 365) * 100))}%`,
                  background:
                    "linear-gradient(90deg,var(--warning),var(--primary))",
                }}
              />
            </div>
            <span className="tag-mono subtle">
              expira {fmtShort(proxima.data_expiracao)}
            </span>
          </div>
        )}
        {/* user */}
        <div
          className="flex center gap-3"
          style={{ padding: "10px 8px", borderTop: "1px solid var(--border)" }}
        >
          <span className="avatar">{initialsOf(aluno.nome)}</span>
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontWeight: 600,
                fontSize: "0.9rem",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {aluno.nome}
            </div>
            <div className="tag-mono cyan">
              {ativas.length} curso{ativas.length === 1 ? "" : "s"} ativo
              {ativas.length === 1 ? "" : "s"}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
