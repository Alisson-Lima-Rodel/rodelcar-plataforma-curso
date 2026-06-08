"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { SectionHead } from "@/components/ui/section-head";
import { PREMIUM, type Course } from "@/lib/portal-data";
import { CourseCarousel } from "./course-carousel";
import { usePortal } from "./portal-context";

export function Vitrine({ courses }: { courses: Course[] }) {
  const { showToast } = usePortal();

  return (
    <section
      id="vitrine"
      className="section blueprint"
      style={{ position: "relative", scrollMarginTop: 80 }}
    >
      <div className="wrap">
        <SectionHead
          eyebrow="Vitrine de formação"
          title="Escolha sua formação"
          sub="Acesso de 1 ano em qualquer compra. Comece pela formação completa ou monte sua trilha por módulos avulsos."
        />

        {/* Featured Premium */}
        <Reveal
          className="card"
          style={{
            padding: 0,
            overflow: "hidden",
            marginBottom: 40,
            border: "1px solid rgba(244,184,96,0.4)",
            boxShadow: "0 30px 80px -40px rgba(229,55,43,0.4)",
          }}
        >
          <div
            className="premium-grid"
            style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr" }}
          >
            <div style={{ padding: "40px 44px" }}>
              <div
                className="flex center gap-3"
                style={{ marginBottom: 18, flexWrap: "wrap" }}
              >
                <Badge variant="premium" icon="award">
                  Premium · Mais completo
                </Badge>
                <Badge variant="cyan" icon="infinity">
                  1 ano de acesso
                </Badge>
              </div>
              <h3
                style={{
                  fontSize: "2.1rem",
                  marginBottom: 14,
                  lineHeight: 1.1,
                }}
              >
                {PREMIUM.title}
              </h3>
              <p
                className="muted"
                style={{ fontSize: "1.02rem", marginBottom: 24, maxWidth: 460 }}
              >
                Tudo o que você precisa para dominar diagnóstico e reparo de
                câmbio automático — do scanner ao overhaul completo.
              </p>
              <ul
                style={{
                  listStyle: "none",
                  display: "grid",
                  gap: 11,
                  marginBottom: 30,
                }}
              >
                {PREMIUM.includes.map((it, i) => (
                  <li
                    key={i}
                    className="flex gap-3"
                    style={{ alignItems: "flex-start" }}
                  >
                    <Icon
                      name="checkCircle"
                      size={19}
                      style={{
                        color: "var(--primary)",
                        flexShrink: 0,
                        marginTop: 1,
                      }}
                    />
                    <span style={{ fontSize: "0.96rem" }}>{it}</span>
                  </li>
                ))}
              </ul>
              <div className="flex center gap-4" style={{ flexWrap: "wrap" }}>
                <Button
                  variant="primary"
                  size="lg"
                  icon="bolt"
                  onClick={() =>
                    showToast({ title: "Compra iniciada", msg: PREMIUM.title })
                  }
                >
                  Assinar Premium
                </Button>
                <div className="flex col" style={{ gap: 2 }}>
                  <div className="flex center gap-2">
                    <span className="price" style={{ fontSize: "2rem" }}>
                      R$ {PREMIUM.price.toLocaleString("pt-BR")}
                    </span>
                    <span className="strike tag-mono">
                      R$ {PREMIUM.old.toLocaleString("pt-BR")}
                    </span>
                  </div>
                  <span className="tag-mono">
                    {PREMIUM.installment} · por ano
                  </span>
                </div>
              </div>
            </div>
            {/* visual side */}
            <div
              className="blueprint-fine blueprint"
              style={{
                position: "relative",
                background:
                  "linear-gradient(150deg, var(--surface-2), var(--surface))",
                borderLeft: "1px solid var(--border)",
                minHeight: 360,
                display: "grid",
                placeItems: "center",
              }}
            >
              <div
                className="glow-amber"
                style={{
                  width: 320,
                  height: 320,
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%,-50%)",
                }}
              />
              <div
                style={{ position: "relative", textAlign: "center", zIndex: 1 }}
              >
                <div
                  style={{
                    width: 96,
                    height: 96,
                    borderRadius: 22,
                    background: "var(--primary-soft)",
                    border: "1px solid rgba(229,55,43,0.4)",
                    display: "grid",
                    placeItems: "center",
                    margin: "0 auto 18px",
                    boxShadow: "var(--glow-soft)",
                  }}
                >
                  <Icon
                    name="award"
                    size={46}
                    style={{ color: "var(--primary)" }}
                  />
                </div>
                <div
                  className="price"
                  style={{ fontSize: "3rem", lineHeight: 1 }}
                >
                  6
                </div>
                <div className="tag-mono" style={{ marginTop: 6 }}>
                  módulos · 1 certificado
                </div>
              </div>
            </div>
          </div>
        </Reveal>

        {/* Module carousel */}
        <div
          className="flex center between"
          style={{ marginBottom: 22, gap: 16, flexWrap: "wrap" }}
        >
          <div>
            <h3 style={{ fontSize: "1.375rem" }}>Módulos avulsos</h3>
            <span className="tag-mono">
              {courses.length} módulos · selo de 1 ano em todos
            </span>
          </div>
          <Link href="/cursos" className="btn btn-secondary">
            <Icon name="book" size={17} />
            Mostrar todos
          </Link>
        </div>
        <Reveal>
          <CourseCarousel courses={courses} />
        </Reveal>
      </div>
    </section>
  );
}
