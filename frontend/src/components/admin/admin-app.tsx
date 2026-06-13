"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/badge";
import { Toast } from "@/components/portal/toast";
import { ENTITIES, type EntityKey } from "@/lib/admin-data";
import { ADMIN_CRUD } from "@/lib/admin-api";
import { useAdmin } from "@/components/providers/admin-provider";
import { AdminSidebar } from "./admin-sidebar";
import { Overview } from "./overview";
import { AdminRefunds } from "./refunds";
import { AdminReviews } from "./reviews-moderation";
import { RemoteEntityManager } from "./remote-entity-manager";

type View = "overview" | "refunds" | "reviews" | EntityKey;

const TITLES: Record<View, { title: string; crumb: string }> = {
  overview: { title: "Visão geral", crumb: "ADMIN" },
  students: { title: "Alunos", crumb: "ADMIN · CADASTROS" },
  courses: { title: "Cursos", crumb: "ADMIN · CADASTROS" },
  testimonials: { title: "Depoimentos", crumb: "ADMIN · CADASTROS" },
  plans: { title: "Planos (assinatura)", crumb: "ADMIN · CADASTROS" },
  refunds: { title: "Reembolsos", crumb: "ADMIN · SUPORTE" },
  reviews: { title: "Avaliações", crumb: "ADMIN · PORTAL" },
  videos: { title: "Vídeos", crumb: "ADMIN · PORTAL" },
  faq: { title: "FAQ", crumb: "ADMIN · PORTAL" },
  admins: { title: "Administradores", crumb: "ADMIN · EQUIPE" },
};

function initialsOf(name: string): string {
  return (name || "?")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function AdminApp() {
  const router = useRouter();
  const { status, admin, logout } = useAdmin();
  const [view, setView] = useState<View>("overview");
  const [toast, setToast] = useState<string | null>(null);
  const [pendingNew, setPendingNew] = useState<EntityKey | null>(null);

  useEffect(() => {
    if (status === "unauthed") router.replace("/login");
  }, [status, router]);

  const nav = (v: string) => {
    setPendingNew(null);
    setView(v as View);
    window.scrollTo(0, 0);
  };
  const newIn = (key: EntityKey) => {
    setView(key);
    setPendingNew(key);
    window.scrollTo(0, 0);
  };

  if (status !== "authed" || !admin) {
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

  const t = TITLES[view];
  const sair = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="app-shell">
      <AdminSidebar view={view} onNav={nav} />
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
            <Badge variant="cyan" icon="shield">
              {admin.papel}
            </Badge>
            <span
              className="avatar"
              style={{
                width: 38,
                height: 38,
                background: "var(--primary)",
                color: "var(--primary-fg)",
                borderColor: "var(--primary)",
              }}
              title={admin.nome}
            >
              {initialsOf(admin.nome)}
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

        {view === "overview" ? (
          <Overview onNav={nav} onNew={newIn} />
        ) : view === "refunds" ? (
          <AdminRefunds onToast={setToast} />
        ) : view === "reviews" ? (
          <AdminReviews onToast={setToast} />
        ) : (
          <RemoteEntityManager
            key={view + (pendingNew === view ? "-new" : "")}
            ent={ENTITIES[view]}
            entityKey={view}
            crud={ADMIN_CRUD[view]}
            autoNew={pendingNew === view}
            onToast={setToast}
          />
        )}
      </main>
      {toast && <Toast msg={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
