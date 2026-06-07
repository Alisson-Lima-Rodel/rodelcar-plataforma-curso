"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { COURSES } from "@/lib/portal-data";
import { CourseCard } from "./course-card";
import { usePortal } from "./portal-context";

export function AllCourses() {
  const { showToast } = usePortal();
  const [filter, setFilter] = useState("Todos");

  const systems = useMemo(() => {
    const counts = new Map<string, number>();
    counts.set("Todos", COURSES.length);
    for (const c of COURSES)
      counts.set(c.badge.label, (counts.get(c.badge.label) ?? 0) + 1);
    return Array.from(counts.entries());
  }, []);

  const list =
    filter === "Todos"
      ? COURSES
      : COURSES.filter((c) => c.badge.label === filter);

  return (
    <div>
      <section
        className="blueprint page-head"
        style={{ paddingTop: 48, paddingBottom: 8 }}
      >
        <div
          className="glow-amber"
          style={{
            width: 520,
            height: 320,
            top: -150,
            left: "50%",
            transform: "translateX(-50%)",
          }}
        />
        <div className="wrap" style={{ position: "relative", zIndex: 1 }}>
          <Link
            href="/#vitrine"
            className="btn btn-ghost btn-sm"
            style={{ marginBottom: 20, paddingLeft: 0 }}
          >
            <Icon name="arrowLeft" size={16} /> Voltar
          </Link>
          <div
            className="eyebrow"
            style={{ marginBottom: 14, color: "var(--primary)" }}
          >
            // Catálogo completo
          </div>
          <h1
            style={{ fontSize: "2.85rem", marginBottom: 14, lineHeight: 1.05 }}
          >
            Todos os cursos
          </h1>
          <p
            className="muted"
            style={{ fontSize: "1.08rem", maxWidth: 600, lineHeight: 1.55 }}
          >
            Câmbios automáticos e automatizados, por sistema. Todos com 1 ano de
            acesso e certificado verificável.
          </p>
        </div>
      </section>

      <section className="section-tight" style={{ paddingTop: 32 }}>
        <div className="wrap">
          <div className="chips">
            {systems.map(([label, count]) => (
              <button
                key={label}
                className={`chip ${filter === label ? "active" : ""}`.trim()}
                onClick={() => setFilter(label)}
              >
                {label}{" "}
                <span className="mono" style={{ opacity: 0.7 }}>
                  {count}
                </span>
              </button>
            ))}
          </div>

          <div className="courses-grid">
            {list.map((c) => (
              <CourseCard key={c.id} c={c} />
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: 48 }}>
            <Button
              variant="primary"
              size="lg"
              icon="award"
              onClick={() =>
                showToast({
                  title: "Compra iniciada",
                  msg: "Formação Completa",
                })
              }
            >
              Ver Formação Completa
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
