"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/badge";
import { STUDENT } from "@/lib/student-data";
import { activeLmsId } from "@/lib/lms-nav";
import { Sidebar } from "./sidebar";

const TITLES: Record<string, { title: string; crumb: string }> = {
  dashboard: { title: "Painel do aluno", crumb: "ÁREA DO ALUNO" },
  player: { title: "Aula em andamento", crumb: "REPRODUTOR" },
  certificate: { title: "Certificado", crumb: "CONQUISTAS" },
};

export function LmsShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const t = TITLES[activeLmsId(pathname)] ?? TITLES.dashboard;

  return (
    <div className="app-shell">
      <Sidebar />
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
            <Badge variant="warning" icon="clock">
              Expira em {STUDENT.daysLeft} dias
            </Badge>
            <button
              className="btn btn-secondary btn-sm"
              style={{ width: 40, padding: 0, height: 40 }}
              aria-label="Mensagens"
            >
              <Icon name="message" size={18} />
            </button>
            <span className="avatar" style={{ width: 38, height: 38 }}>
              {STUDENT.initials}
            </span>
          </div>
        </div>
        {children as ReactNode}
      </main>
    </div>
  );
}
