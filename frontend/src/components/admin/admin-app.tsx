"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Toast } from "@/components/portal/toast";
import {
  ADMIN_USER,
  ENTITIES,
  ENTITY_KEYS,
  type AdminItem,
  type EntityKey,
} from "@/lib/admin-data";
import { AdminSidebar } from "./admin-sidebar";
import { Overview } from "./overview";
import { EntityManager } from "./entity-manager";

type View = "overview" | EntityKey;

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

export function AdminApp() {
  const [view, setView] = useState<View>("overview");
  const [data, setData] = useState<Record<EntityKey, AdminItem[]>>(seedData);
  const [toast, setToast] = useState<string | null>(null);
  const [pendingNew, setPendingNew] = useState<EntityKey | null>(null);

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

  const t = TITLES[view];

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
              Modo administrador
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
            >
              {ADMIN_USER.initials}
            </span>
          </div>
        </div>

        {view === "overview" && (
          <Overview data={data} onNav={nav} onNew={newIn} />
        )}
        {view !== "overview" && (
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
