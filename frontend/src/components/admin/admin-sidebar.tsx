"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Logo } from "@/components/ui/logo";
import { ADMIN_USER } from "@/lib/admin-data";

const NAV: { id: string; label: string; icon: string }[] = [
  { id: "overview", label: "Visão geral", icon: "gauge" },
  { id: "students", label: "Alunos", icon: "users" },
  { id: "courses", label: "Cursos", icon: "book" },
  { id: "testimonials", label: "Depoimentos", icon: "message" },
  { id: "plans", label: "Planos", icon: "infinity" },
  { id: "videos", label: "Vídeos", icon: "play" },
  { id: "faq", label: "FAQ", icon: "book" },
  { id: "admins", label: "Administradores", icon: "shield" },
];

export function AdminSidebar({
  view,
  onNav,
}: {
  view: string;
  onNav: (v: string) => void;
}) {
  return (
    <aside className="sidebar">
      <Link
        href="/"
        style={{ padding: "4px 10px 8px", display: "inline-block" }}
        aria-label="Início"
      >
        <Logo size="md" tagline={false} />
      </Link>
      <div
        className="tag-mono"
        style={{ padding: "0 12px 20px", color: "var(--text-subtle)" }}
      >
        // ADMIN
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {NAV.map((it) => (
          <button
            key={it.id}
            className={`nav-item ${view === it.id ? "active" : ""}`.trim()}
            onClick={() => onNav(it.id)}
          >
            <Icon name={it.icon} size={19} />
            {it.label}
          </button>
        ))}
      </nav>

      <div style={{ marginTop: "auto" }}>
        <Link
          href="/"
          className="nav-item"
          style={{ textDecoration: "none", marginBottom: 8 }}
        >
          <Icon
            name="arrow"
            size={18}
            style={{ transform: "rotate(-45deg)" }}
          />
          Ver site público
        </Link>
        <div
          className="flex center gap-3"
          style={{ padding: "12px 8px", borderTop: "1px solid var(--border)" }}
        >
          <span
            className="avatar"
            style={{
              background: "var(--primary)",
              color: "var(--primary-fg)",
              borderColor: "var(--primary)",
            }}
          >
            {ADMIN_USER.initials}
          </span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
              {ADMIN_USER.name}
            </div>
            <div className="tag-mono cyan">{ADMIN_USER.role}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
