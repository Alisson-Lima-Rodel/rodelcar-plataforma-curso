"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/badge";
import { Toast } from "@/components/portal/toast";
import {
  ENTITIES,
  ENTITY_KEYS,
  type AdminItem,
  type EntityKey,
} from "@/lib/admin-data";
import { ADMIN_CRUD } from "@/lib/admin-api";
import { useAdmin } from "@/components/providers/admin-provider";
import { AdminSidebar } from "./admin-sidebar";
import { Overview } from "./overview";
import { EntityManager } from "./entity-manager";
import { RemoteEntityManager } from "./remote-entity-manager";

type View = "overview" | EntityKey;

// Entidades já ligadas ao backend real (as demais seguem em memória por ora).
const REMOTE: EntityKey[] = ["courses", "testimonials", "packages", "admins"];

const TITLES: Record<View, { title: string; crumb: string }> = {
  overview: { title: "Visão geral", crumb: "ADMIN" },
  students: { title: "Alunos", crumb: "ADMIN · CADASTROS" },
  courses: { title: "Cursos", crumb: "ADMIN · CADASTROS" },
  testimonials: { title: "Depoimentos", crumb: "ADMIN · CADASTROS" },
  packages: { title: "Pacotes", crumb: "ADMIN · CADASTROS" },
  admins: { title: "Administradores", crumb: "ADMIN · EQUIPE" },
};

function seedData(): Record<EntityKey, AdminItem[]> {
  const d = {} as Record<EntityKey, AdminItem[]>;
  ENTITY_KEYS.forEach((k) => {
    d[k] = ENTITIES[k].seed.map((x) => ({ ...x }));
  });
  return d;
}

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
  const [data, setData] = useState<Record<EntityKey, AdminItem[]>>(seedData);
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

  const onSave = (key: EntityKey, item: AdminItem) =>
    setData((d) => {
      const exists = d[key].some((x) => x.id === item.id);
      return {
        ...d,
        [key]: exists
          ? d[key].map((x) => (x.id === item.id ? item : x))
          : [item, ...d[key]],
      };
    });
  const onDelete = (key: EntityKey, id: string) =>
    setData((d) => ({ ...d, [key]: d[key].filter((x) => x.id !== id) }));

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

        {view === "overview" && (
          <Overview data={data} onNav={nav} onNew={newIn} />
        )}
        {view !== "overview" && REMOTE.includes(view) && (
          <RemoteEntityManager
            key={view + (pendingNew === view ? "-new" : "")}
            ent={ENTITIES[view]}
            entityKey={view}
            crud={ADMIN_CRUD[view]}
            autoNew={pendingNew === view}
            onToast={setToast}
          />
        )}
        {view !== "overview" && !REMOTE.includes(view) && (
          <EntityManager
            key={view + (pendingNew === view ? "-new" : "")}
            ent={ENTITIES[view]}
            items={data[view]}
            onSave={(item) => onSave(view, item)}
            onDelete={(id) => onDelete(view, id)}
            onToast={setToast}
            autoNew={pendingNew === view}
          />
        )}
      </main>
      {toast && <Toast msg={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
