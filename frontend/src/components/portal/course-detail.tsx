"use client";

import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Stars } from "@/components/ui/stars";
import { Reveal } from "@/components/ui/reveal";
import { type Course, type CourseModule, type Faq } from "@/lib/portal-data";
import { usePortal } from "./portal-context";
import { useCompra } from "./use-compra";

function AccItem({
  m,
  idx,
  open,
  onToggle,
}: {
  m: CourseModule;
  idx: number;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="acc-item">
      <button className="acc-head" onClick={onToggle} aria-expanded={open}>
        <span
          className="mono"
          style={{ fontSize: "0.8rem", color: "var(--primary)", width: 28 }}
        >
          {String(idx + 1).padStart(2, "0")}
        </span>
        <span style={{ fontWeight: 600, fontSize: "1rem", flex: 1 }}>
          {m.t}
        </span>
        <span className="tag-mono" style={{ marginRight: 12 }}>
          {m.lessons.length} aulas
        </span>
        <Icon
          name="chevron"
          size={18}
          style={{
            color: "var(--text-muted)",
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 220ms",
          }}
        />
      </button>
      <div
        className="acc-body"
        style={{ maxHeight: open ? m.lessons.length * 56 + 8 : 0 }}
      >
        <div style={{ padding: "4px 18px 10px" }}>
          {m.lessons.map((l, i) => (
            <div
              key={i}
              className="flex center between"
              style={{
                padding: "11px 0",
                borderTop: i ? "1px solid var(--border)" : "none",
              }}
            >
              <span className="flex center gap-3">
                <Icon
                  name="play"
                  size={13}
                  style={{ color: "var(--text-subtle)" }}
                />
                <span
                  style={{ fontSize: "0.92rem", color: "var(--text-muted)" }}
                >
                  {l}
                </span>
              </span>
              <span className="tag-mono">{m.dur[i]}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function FaqItem({ f }: { f: Faq }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="acc-item">
      <button
        className="acc-head"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span style={{ fontWeight: 600, fontSize: "1rem", flex: 1 }}>
          {f.q}
        </span>
        <Icon
          name="chevron"
          size={18}
          style={{
            color: "var(--text-muted)",
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 220ms",
          }}
        />
      </button>
      <div className="acc-body" style={{ maxHeight: open ? 200 : 0 }}>
        <p
          className="muted"
          style={{
            padding: "2px 18px 16px",
            fontSize: "0.94rem",
            lineHeight: 1.55,
          }}
        >
          {f.a}
        </p>
      </div>
    </div>
  );
}

export function CourseDetail({
  course,
  faqs = [],
}: {
  course: Course;
  faqs?: Faq[];
}) {
  const { openSchedule } = usePortal();
  const { iniciarCompra, comprando } = useCompra();
  const rich = course;
  const modules = rich.modules ?? [];
  const learn = rich.learn ?? [];
  const [openMod, setOpenMod] = useState(0);
  const [tab, setTab] = useState<"conteudo" | "aprende">("conteudo");
  // Course.id carrega o slug do curso (mapBase em lib/api.ts).
  const enroll = () => iniciarCompra({ tipo: "curso", slug: rich.id });
  const discount = rich.old ? Math.round((1 - rich.price / rich.old) * 100) : 0;

  return (
    <div>
      {/* breadcrumb + hero */}
      <section
        className="blueprint"
        style={{
          position: "relative",
          overflow: "hidden",
          paddingTop: 36,
          paddingBottom: 56,
        }}
      >
        <div
          className="glow-amber"
          style={{ width: 560, height: 360, top: -160, right: -80 }}
        />
        <div className="wrap" style={{ position: "relative", zIndex: 1 }}>
          <Link
            href="/#vitrine"
            className="btn btn-ghost btn-sm"
            style={{ marginBottom: 24, paddingLeft: 0 }}
          >
            <Icon name="arrowLeft" size={16} /> Voltar à vitrine
          </Link>
          <div
            className="detail-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "1.5fr 1fr",
              gap: 48,
              alignItems: "start",
            }}
          >
            {/* left content */}
            <div>
              <div
                className="flex center gap-3"
                style={{ marginBottom: 18, flexWrap: "wrap" }}
              >
                <Badge variant="amber" icon={rich.icon}>
                  {rich.level}
                </Badge>
                <Badge variant="cyan" icon="infinity">
                  1 ano de acesso
                </Badge>
                <span className="flex center gap-2">
                  <Stars value={rich.rating} size={15} />
                  <span className="tag-mono">
                    {rich.rating} · {rich.students.toLocaleString("pt-BR")}{" "}
                    alunos
                  </span>
                </span>
              </div>
              <h1
                style={{
                  fontSize: "2.85rem",
                  marginBottom: 18,
                  lineHeight: 1.05,
                }}
              >
                {rich.title}
              </h1>
              <p
                style={{
                  fontSize: "1.18rem",
                  color: "var(--text-muted)",
                  maxWidth: 580,
                  lineHeight: 1.5,
                  marginBottom: 28,
                }}
              >
                {rich.tagline}
              </p>
              <div className="flex center gap-6" style={{ flexWrap: "wrap" }}>
                {(
                  [
                    ["clock", rich.hours, "de vídeo"],
                    [
                      "book",
                      rich.lessons + " aulas",
                      "em " + modules.length + " módulos",
                    ],
                    ["award", "Certificado", "verificável"],
                    ["users", "Comunidade", "fechada"],
                  ] as [string, string, string][]
                ).map(([ic, a, b], i) => (
                  <div key={i} className="flex center gap-3">
                    <Icon
                      name={ic}
                      size={20}
                      style={{ color: "var(--primary)" }}
                    />
                    <div>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: "0.95rem",
                          lineHeight: 1.1,
                        }}
                      >
                        {a}
                      </div>
                      <div className="tag-mono">{b}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* tab selector */}
              <div
                style={{
                  marginTop: 36,
                  borderTop: "1px solid var(--border)",
                  paddingTop: 28,
                }}
              >
                <div className="flex center gap-2" style={{ marginBottom: 20 }}>
                  <button
                    onClick={() => setTab("conteudo")}
                    className={`btn btn-sm ${tab === "conteudo" ? "btn-secondary" : "btn-ghost"}`}
                  >
                    Conteúdo do curso
                  </button>
                  <button
                    onClick={() => setTab("aprende")}
                    className={`btn btn-sm ${tab === "aprende" ? "btn-secondary" : "btn-ghost"}`}
                  >
                    O que você aprende
                  </button>
                </div>

                {tab === "conteudo" && (
                  <div>
                    <div
                      className="flex center between"
                      style={{ marginBottom: 18 }}
                    >
                      <span className="tag-mono">
                        {modules.length} módulos · {rich.lessons} aulas ·{" "}
                        {rich.hours}
                      </span>
                    </div>
                    <div style={{ display: "grid", gap: 10 }}>
                      {modules.map((m, i) => (
                        <AccItem
                          key={i}
                          m={m}
                          idx={i}
                          open={openMod === i}
                          onToggle={() => setOpenMod(openMod === i ? -1 : i)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {tab === "aprende" && (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 16,
                    }}
                  >
                    {learn.map((l, i) => (
                      <div
                        key={i}
                        className="flex gap-3"
                        style={{
                          alignItems: "flex-start",
                          padding: "16px 18px",
                          background: "var(--surface)",
                          border: "1px solid var(--border)",
                          borderRadius: 10,
                        }}
                      >
                        <Icon
                          name="checkCircle"
                          size={20}
                          style={{
                            color: "var(--primary)",
                            flexShrink: 0,
                            marginTop: 1,
                          }}
                        />
                        <span style={{ fontSize: "0.95rem", lineHeight: 1.4 }}>
                          {l}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* right — purchase card */}
            <Reveal
              className="card detail-purchase"
              style={{
                padding: 0,
                overflow: "hidden",
                position: "sticky",
                top: 90,
                boxShadow: "0 30px 70px -36px rgba(0,0,0,0.7)",
              }}
            >
              <div
                className="thumb"
                style={{
                  borderRadius: 0,
                  border: "none",
                  borderBottom: "1px solid var(--border)",
                  ...(rich.cover
                    ? {
                        backgroundImage: `url(${rich.cover})`,
                        backgroundSize: "cover",
                        backgroundPosition: "center",
                      }
                    : {}),
                }}
              >
                <div className="play-btn">
                  <Icon name="play" size={20} />
                </div>
                {!rich.cover && (
                  <span className="thumb-label">[ trailer · 16:9 ]</span>
                )}
              </div>
              <div style={{ padding: 22 }}>
                <div className="flex center gap-2" style={{ marginBottom: 6 }}>
                  <span className="price" style={{ fontSize: "2.2rem" }}>
                    R$ {rich.price}
                  </span>
                  {rich.old && (
                    <span className="strike tag-mono">R$ {rich.old}</span>
                  )}
                  {discount > 0 && (
                    <Badge variant="success" style={{ marginLeft: "auto" }}>
                      -{discount}%
                    </Badge>
                  )}
                </div>
                <span
                  className="tag-mono"
                  style={{ display: "block", marginBottom: 18 }}
                >
                  ou 12x de R$ {(rich.price / 12).toFixed(2).replace(".", ",")}
                </span>
                <Button
                  variant="primary"
                  size="lg"
                  block
                  icon="bolt"
                  onClick={enroll}
                  disabled={comprando}
                >
                  {comprando ? "Abrindo pagamento..." : "Comprar agora"}
                </Button>
                <Button
                  variant="secondary"
                  block
                  icon="calendar"
                  onClick={openSchedule}
                >
                  Falar com especialista
                </Button>
                <div className="hr" style={{ margin: "18px 0" }} />
                <ul style={{ listStyle: "none", display: "grid", gap: 10 }}>
                  {(
                    [
                      ["infinity", "1 ano de acesso completo"],
                      ["download", "Materiais e PDFs para download"],
                      ["award", "Certificado verificável"],
                      ["shield", "7 dias de garantia"],
                    ] as [string, string][]
                  ).map(([ic, t], i) => (
                    <li key={i} className="flex center gap-3">
                      <Icon
                        name={ic}
                        size={17}
                        style={{ color: "var(--success)" }}
                      />
                      <span style={{ fontSize: "0.9rem" }}>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Premium + FAQ */}
      <section className="section-tight" style={{ paddingTop: 0 }}>
        <div className="wrap" style={{ maxWidth: 820, marginLeft: 0 }}>
          <div
            className="card blueprint"
            style={{
              padding: 22,
              position: "relative",
              overflow: "hidden",
              marginBottom: 48,
            }}
          >
            <Badge variant="premium" icon="award">
              Economize no Premium
            </Badge>
            <p
              style={{
                fontSize: "0.95rem",
                margin: "14px 0 16px",
                lineHeight: 1.45,
              }}
            >
              Leve este e os outros 5 módulos na{" "}
              <strong>Formação Completa</strong> por uma fração do valor avulso.
            </p>
            <Link href="/#vitrine" className="btn btn-secondary btn-block">
              Ver Premium
              <Icon name="arrow" size={17} />
            </Link>
          </div>
          {faqs.length > 0 && (
            <div>
              <h2 style={{ fontSize: "1.6rem", marginBottom: 20 }}>
                Perguntas frequentes
              </h2>
              <div style={{ display: "grid", gap: 10 }}>
                {faqs.map((f, i) => (
                  <FaqItem key={i} f={f} />
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* final CTA */}
      <section className="section-tight">
        <div className="wrap">
          <div
            className="card blueprint"
            style={{
              padding: "48px 44px",
              textAlign: "center",
              position: "relative",
              overflow: "hidden",
              border: "1px solid var(--border-strong)",
            }}
          >
            <div
              className="glow-amber"
              style={{
                width: 480,
                height: 300,
                top: -120,
                left: "50%",
                transform: "translateX(-50%)",
              }}
            />
            <div style={{ position: "relative", zIndex: 1 }}>
              <h2 style={{ fontSize: "2.2rem", marginBottom: 14 }}>
                Pronto para parar de trocar peça no chute?
              </h2>
              <p
                className="muted"
                style={{
                  fontSize: "1.08rem",
                  maxWidth: 520,
                  margin: "0 auto 28px",
                }}
              >
                Acesso imediato, 1 ano de conteúdo e 7 dias de garantia. Comece
                hoje.
              </p>
              <div
                className="flex center gap-3"
                style={{ justifyContent: "center", flexWrap: "wrap" }}
              >
                <Button
                  variant="primary"
                  size="lg"
                  icon="bolt"
                  onClick={enroll}
                  disabled={comprando}
                >
                  {comprando
                    ? "Abrindo pagamento..."
                    : `Comprar por R$ ${rich.price}`}
                </Button>
                <Button
                  variant="secondary"
                  size="lg"
                  icon="calendar"
                  onClick={openSchedule}
                >
                  Agendar avaliação
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
