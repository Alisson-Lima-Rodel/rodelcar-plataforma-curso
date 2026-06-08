"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { Icon } from "@/components/ui/icon";
import { activeLmsId } from "@/lib/lms-nav";
import { useAuth } from "@/components/providers/auth-provider";
import { Sidebar } from "./sidebar";

const TITLES: Record<string, { title: string; crumb: string }> = {
  dashboard: { title: "Painel do aluno", crumb: "ÁREA DO ALUNO" },
  player: { title: "Aula em andamento", crumb: "REPRODUTOR" },
  certificate: { title: "Certificado", crumb: "CONQUISTAS" },
};

export function initialsOf(name: string): string {
  return (name || "?")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function LmsShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, aluno, logout } = useAuth();
  const t = TITLES[activeLmsId(pathname)] ?? TITLES.dashboard;

  // Guarda de rota: sem sessão → manda pro login.
  useEffect(() => {
    if (status === "unauthed") router.replace("/login");
  }, [status, router]);

  if (status !== "authed" || !aluno) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "var(--bg)",
        }}
      >
        <span className="tag-mono muted">Carregando…</span>
      </div>
    );
  }

  const sair = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <div className="app-shell">
      <Sidebar aluno={aluno} />
      <main style={{ minWidth: 0, display: "flex", flexDirection: "column" }}>
        <div className="topbar">
          <div>
            <div className="tag-mono" style={{ marginBottom: 3 }}>
              {t.crumb}
            </div>
            <h3 style={{ fontSize: "1.15rem", whiteSpace: "nowrap" }}>
              {t.title}
            </h3>
          </div>
          <div className="flex center gap-3">
            <span className="avatar" style={{ width: 38, height: 38 }}>
              {initialsOf(aluno.nome)}
            </span>
            <button
              onClick={sair}
              className="btn btn-secondary btn-sm"
              aria-label="Sair"
            >
              <Icon name="lock" size={16} /> Sair
            </button>
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}
