"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { PREMIUM, type Course } from "@/lib/portal-data";
import { type PlanoPublico } from "@/lib/api";
import { CourseCard } from "./course-card";
import { usePortal } from "./portal-context";
import { useCompra } from "./use-compra";

export function AllCourses({
  courses,
  planoAnual,
}: {
  courses: Course[];
  planoAnual: PlanoPublico | null;
}) {
  const { showToast } = usePortal();
  const { iniciarCompra, comprando } = useCompra();
  const [filter, setFilter] = useState("Todos");

  // Preço real vem do plano (backend); o estático é só fallback de exibição.
  const precoPremium = planoAnual?.preco ?? PREMIUM.price;
  const parcelaPremium = `12x de R$ ${(precoPremium / 12)
    .toFixed(2)
    .replace(".", ",")}`;
  const assinarPremium = () => {
    if (!planoAnual) {
      showToast({
        title: "Indisponível no momento",
        msg: "A Formação Completa está temporariamente indisponível.",
      });
      return;
    }
    iniciarCompra({ tipo: "plano", planoId: planoAnual.id });
  };

  const systems = useMemo(() => {
    const counts = new Map<string, number>();
    counts.set("Todos", courses.length);
    for (const c of courses)
      counts.set(c.badge.label, (counts.get(c.badge.label) ?? 0) + 1);
    return Array.from(counts.entries());
  }, [courses]);

  const list =
    filter === "Todos"
      ? courses
      : courses.filter((c) => c.badge.label === filter);

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

      {planoAnual && (
        <section
          className="section-tight"
          style={{ paddingTop: 28, paddingBottom: 0 }}
        >
          <div className="wrap">
            <Reveal
              className="card"
              style={{
                padding: "28px 32px",
                border: "1px solid rgba(244,184,96,0.4)",
                boxShadow: "0 30px 80px -40px rgba(229,55,43,0.4)",
              }}
            >
              <div
                className="flex center gap-3"
                style={{ marginBottom: 14, flexWrap: "wrap" }}
              >
                <Badge variant="premium" icon="award">
                  Formação Completa · Premium
                </Badge>
                <Badge variant="cyan" icon="infinity">
                  Todos os cursos · 1 ano de acesso
                </Badge>
              </div>
              <h2
                style={{
                  fontSize: "1.9rem",
                  marginBottom: 10,
                  lineHeight: 1.1,
                }}
              >
                {PREMIUM.title}
              </h2>
              <p
                className="muted"
                style={{ fontSize: "1rem", marginBottom: 22, maxWidth: 560 }}
              >
                Acesso a todos os módulos do catálogo, do scanner ao overhaul,
                por uma fração do valor avulso. Ou monte sua trilha por módulos
                avulsos abaixo.
              </p>
              <div className="flex center gap-4" style={{ flexWrap: "wrap" }}>
                <Button
                  variant="primary"
                  size="lg"
                  icon="bolt"
                  onClick={assinarPremium}
                  disabled={comprando}
                >
                  {comprando
                    ? "Abrindo pagamento..."
                    : "Assinar Formação Completa"}
                </Button>
                <div className="flex col" style={{ gap: 2 }}>
                  <span className="price" style={{ fontSize: "1.8rem" }}>
                    R$ {precoPremium.toLocaleString("pt-BR")}
                  </span>
                  <span className="tag-mono">{parcelaPremium} · por ano</span>
                </div>
              </div>
            </Reveal>
          </div>
        </section>
      )}

      <section className="section-tight" style={{ paddingTop: 32 }}>
        <div className="wrap">
          <h3 style={{ fontSize: "1.375rem", marginBottom: 16 }}>
            Módulos avulsos
          </h3>
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

          {planoAnual && (
            <div style={{ textAlign: "center", marginTop: 48 }}>
              <Button
                variant="primary"
                size="lg"
                icon="award"
                onClick={assinarPremium}
                disabled={comprando}
              >
                {comprando
                  ? "Abrindo pagamento..."
                  : "Assinar Formação Completa"}
              </Button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
