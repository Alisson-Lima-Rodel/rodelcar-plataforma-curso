"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
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
  const [navOpen, setNavOpen] = useState(false);
  // Durante o "Sair" vamos DIRETO ao site público — o guard abaixo não deve
  // mandar para /login nesse intervalo (senão pisca o login antes de ir para /).
  const saindo = useRef(false);

  // Guarda de rota: sem sessão → manda pro login (exceto durante o logout).
  useEffect(() => {
    if (status === "unauthed" && !saindo.current) router.replace("/login");
  }, [status, router]);

  // Fecha a gaveta ao trocar de rota e trava o scroll do corpo enquanto aberta.
  useEffect(() => setNavOpen(false), [pathname]);
  useEffect(() => {
    document.body.style.overflow = navOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [navOpen]);

  if (status !== "authed" || !aluno) {
    return (
      // suppressHydrationWarning: tela de "carregando" determinística; se uma
      // extensão do navegador injetar um nó aqui antes da hidratação, não dispara
      // o falso "hydration failed" (só de dev).
      <div
        suppressHydrationWarning
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
    saindo.current = true; // impede o guard de piscar /login
    try {
      await logout();
    } finally {
      // Vai DIRETO ao site público mesmo se o logout falhar (navegação "dura").
      window.location.assign("/");
    }
  };

  return (
    <div className={`app-shell${navOpen ? " nav-open" : ""}`}>
      <div
        className="nav-scrim"
        onClick={() => setNavOpen(false)}
        aria-hidden="true"
      />
      <Sidebar aluno={aluno} onNavigate={() => setNavOpen(false)} />
      <main style={{ minWidth: 0, display: "flex", flexDirection: "column" }}>
        <div className="topbar">
          <button
            className="topbar-burger"
            onClick={() => setNavOpen(true)}
            aria-label="Abrir menu"
          >
            <Icon name="menu" size={20} />
          </button>
          <div style={{ minWidth: 0, flex: 1 }}>
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
