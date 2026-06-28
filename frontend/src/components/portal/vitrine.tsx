"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { SectionHead } from "@/components/ui/section-head";
import { PREMIUM, type Course } from "@/lib/portal-data";
import { type PlanoPublico } from "@/lib/api";
import { CourseCarousel } from "./course-carousel";
import { usePortal } from "./portal-context";
import { useCompra } from "./use-compra";

export function Vitrine({
  courses,
  planos,
}: {
  courses: Course[];
  planos: PlanoPublico[];
}) {
  const { showToast } = usePortal();
  const { iniciarCompra, comprando } = useCompra();
  // Plano em destaque no card (anual, ou o 1º ativo); os DEMAIS planos ativos
  // viram uma lista logo abaixo — tudo dinâmico pelo que está cadastrado/ativo.
  const planoAnual =
    planos.find((p) => p.intervalo === "anual") ?? planos[0] ?? null;
  const outrosPlanos = planos.filter((p) => p.id !== planoAnual?.id);
  // Preço real vem do plano (backend); o estático é só fallback de exibição.
  const precoPremium = planoAnual?.preco ?? PREMIUM.price;
  const parcelaPremium = `12x de R$ ${(precoPremium / 12)
    .toFixed(2)
    .replace(".", ",")}`;
  const assinarPlanoPub = (plano: PlanoPublico | null) => {
    if (!plano) {
      showToast({
        title: "Indisponível no momento",
        msg: "A assinatura Premium está temporariamente indisponível.",
      });
      return;
    }
    iniciarCompra({ tipo: "plano", planoId: plano.id });
  };
  const assinarPremium = () => assinarPlanoPub(planoAnual);

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

        {/* Featured Premium — só quando há plano ATIVO (some se todos forem desativados) */}
        {planoAnual && (
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
                  style={{
                    fontSize: "1.02rem",
                    marginBottom: 24,
                    maxWidth: 460,
                  }}
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
                    onClick={assinarPremium}
                    disabled={comprando}
                  >
                    {comprando ? "Abrindo pagamento..." : "Assinar Premium"}
                  </Button>
                  <div className="flex col" style={{ gap: 2 }}>
                    <div className="flex center gap-2">
                      <span className="price" style={{ fontSize: "2rem" }}>
                        R$ {precoPremium.toLocaleString("pt-BR")}
                      </span>
                      {!planoAnual && (
                        <span className="strike tag-mono">
                          R$ {PREMIUM.old.toLocaleString("pt-BR")}
                        </span>
                      )}
                    </div>
                    <span className="tag-mono">{parcelaPremium} · por ano</span>
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
                  style={{
                    position: "relative",
                    textAlign: "center",
                    zIndex: 1,
                  }}
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
        )}

        {/* Outros planos ativos (dinâmico pelo cadastro do admin) */}
        {outrosPlanos.length > 0 && (
          <Reveal style={{ marginBottom: 40 }}>
            <div
              className="flex center between"
              style={{ marginBottom: 14, gap: 12, flexWrap: "wrap" }}
            >
              <h3 style={{ fontSize: "1.2rem" }}>Outros planos</h3>
              <span className="tag-mono">acesso total ao catálogo</span>
            </div>
            <div style={{ display: "grid", gap: 12 }}>
              {outrosPlanos.map((p) => (
                <div
                  key={p.id}
                  className="card flex center between"
                  style={{ padding: "16px 20px", gap: 16, flexWrap: "wrap" }}
                >
                  <div className="flex center gap-3">
                    <Badge variant="premium" icon="award">
                      {p.nome}
                    </Badge>
                    <span className="tag-mono">
                      {p.intervalo === "mensal"
                        ? "cobrança mensal"
                        : p.intervalo === "anual"
                          ? "cobrança anual"
                          : p.intervalo}
                    </span>
                  </div>
                  <div
                    className="flex center gap-4"
                    style={{ flexWrap: "wrap" }}
                  >
                    <span className="price" style={{ fontSize: "1.5rem" }}>
                      R$ {p.preco.toLocaleString("pt-BR")}
                      <span className="tag-mono" style={{ marginLeft: 6 }}>
                        /{p.intervalo === "mensal" ? "mês" : "ano"}
                      </span>
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      icon="bolt"
                      onClick={() => assinarPlanoPub(p)}
                      disabled={comprando}
                    >
                      Assinar
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        )}

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
