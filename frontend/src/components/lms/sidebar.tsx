"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/ui/logo";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/badge";
import { STUDENT } from "@/lib/student-data";
import { activeLmsId, lmsHref } from "@/lib/lms-nav";
import type { Me } from "@/lib/auth-api";
import { initialsOf } from "./lms-shell";

const ITEMS: { id: string; label: string; icon: string }[] = [
  { id: "dashboard", label: "Painel", icon: "gauge" },
  { id: "player", label: "Continuar curso", icon: "play" },
  { id: "courses", label: "Meus cursos", icon: "book" },
  { id: "certificate", label: "Certificados", icon: "award" },
  { id: "community", label: "Comunidade", icon: "users" },
];

export function Sidebar({ aluno }: { aluno: Me }) {
  const pathname = usePathname();
  const active = activeLmsId(pathname);

  return (
    <aside className="sidebar">
      <Link
        href="/"
        style={{ padding: "4px 10px 22px", display: "inline-block" }}
        aria-label="Início"
      >
        <Logo size="md" tagline={false} />
      </Link>

      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {ITEMS.map((it) => (
          <Link
            key={it.id}
            href={lmsHref(it.id)}
            className={`nav-item ${active === it.id ? "active" : ""}`.trim()}
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
        {/* vigência mini */}
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
            <Badge variant="warning">{STUDENT.daysLeft} dias</Badge>
          </div>
          <div className="progress" style={{ marginBottom: 8 }}>
            <span
              style={{
                width: "62%",
                background:
                  "linear-gradient(90deg,var(--warning),var(--primary))",
              }}
            />
          </div>
          <span className="tag-mono subtle">expira {STUDENT.expires}</span>
        </div>
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
            <div className="tag-mono cyan">{STUDENT.plan}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
