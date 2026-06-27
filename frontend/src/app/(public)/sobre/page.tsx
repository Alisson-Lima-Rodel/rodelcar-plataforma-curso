import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Stat } from "@/components/ui/stat";
import { Reveal } from "@/components/ui/reveal";
import { SectionHead } from "@/components/ui/section-head";
import { JsonLd } from "@/components/seo/json-ld";
import { BRAND } from "@/lib/portal-data";
import { SITE_URL } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Sobre a Rödelcar",
  description:
    "A RödelCar é referência em câmbio automático e automatizado em Canoas-RS: Dualogic, PowerShift, iMotion, Easytronic e DSG. Diagnóstico de bancada e formação técnica para mecânicos.",
  alternates: { canonical: "/sobre" },
};

// Sistemas que a oficina domina (cabeçalho de portal-data.ts).
const SISTEMAS: [string, string][] = [
  ["Fiat Dualogic", "gauge"],
  ["Ford PowerShift", "bolt"],
  ["VW DSG DQ200/DQ250", "spark"],
  ["GM Easytronic", "wrench"],
  ["Renault iMotion", "gauge"],
  ["Automático convencional", "infinity"],
];

const ATUACAO: [string, string, string][] = [
  [
    "Diagnóstico de bancada",
    "gauge",
    "Leitura do problema na origem — sem achismo e sem trocar peça à toa.",
  ],
  [
    "Reparo especializado",
    "wrench",
    "Atuador, embreagem, mecatrônica e calibração nos câmbios automatizados.",
  ],
  [
    "Formação técnica",
    "book",
    "Cursos online e turmas presenciais para mecânicos subirem de nível.",
  ],
];

export default function SobrePage() {
  const jsonld = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    "@id": `${SITE_URL}/sobre`,
    url: `${SITE_URL}/sobre`,
    name: "Sobre a RödelCar Câmbios",
    about: { "@id": `${SITE_URL}/#org` },
  };

  return (
    <main>
      <JsonLd data={jsonld} />
      <section className="section">
        <div className="wrap">
          <div style={{ maxWidth: 760, margin: "0 0 44px" }}>
            <div style={{ marginBottom: 18 }}>
              <Badge variant="amber" icon="spark">
                Especializada em câmbios · {BRAND.city}
              </Badge>
            </div>
            <h1
              style={{ fontSize: "2.8rem", lineHeight: 1.08, marginBottom: 18 }}
            >
              Especialistas em câmbio{" "}
              <span className="amber">automático e automatizado.</span>
            </h1>
            <p
              style={{
                fontSize: "1.12rem",
                color: "var(--text-muted)",
                lineHeight: 1.6,
              }}
            >
              A <strong style={{ color: "var(--text)" }}>Rödelcar</strong> é
              referência em Dualogic, PowerShift, iMotion, Easytronic e DSG.
              Diagnóstico de bancada, sem achismo e sem peça trocada à toa — e a
              mesma experiência vira formação técnica para mecânicos de todo o
              Brasil.
            </p>
          </div>

          {/* Números */}
          <Reveal
            className="flex center"
            style={{
              gap: 28,
              padding: "26px 0",
              borderTop: "1px solid var(--border)",
              borderBottom: "1px solid var(--border)",
              flexWrap: "wrap",
              marginBottom: 56,
            }}
          >
            <Stat value="+12" label="sistemas dominados" accent />
            <div
              style={{ width: 1, height: 38, background: "var(--border)" }}
            />
            <Stat value="+2.000" label="mecânicos formados" accent />
            <div
              style={{ width: 1, height: 38, background: "var(--border)" }}
            />
            <Stat value="+5.400" label="câmbios reparados" accent />
          </Reveal>

          {/* Sistemas */}
          <SectionHead
            eyebrow="Sistemas que dominamos"
            title="Do automatizado ao automático convencional"
          />
          <Reveal
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 16,
              marginBottom: 64,
            }}
          >
            {SISTEMAS.map(([nome, ic]) => (
              <div
                key={nome}
                className="card"
                style={{
                  padding: 18,
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                }}
              >
                <span
                  style={{
                    width: 42,
                    height: 42,
                    borderRadius: 10,
                    display: "grid",
                    placeItems: "center",
                    background: "var(--surface-2)",
                    color: "var(--primary)",
                    border: "1px solid var(--border)",
                    flexShrink: 0,
                  }}
                >
                  <Icon name={ic} size={19} />
                </span>
                <strong style={{ fontSize: "0.98rem" }}>{nome}</strong>
              </div>
            ))}
          </Reveal>

          {/* O que fazemos */}
          <SectionHead
            eyebrow="O que fazemos"
            title="Diagnóstico, reparo e formação"
          />
          <Reveal
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: 18,
              marginBottom: 56,
            }}
          >
            {ATUACAO.map(([t, ic, d]) => (
              <div key={t} className="card" style={{ padding: 24 }}>
                <span
                  style={{
                    width: 46,
                    height: 46,
                    borderRadius: 11,
                    display: "grid",
                    placeItems: "center",
                    background: "var(--primary-soft)",
                    color: "var(--primary)",
                    border: "1px solid var(--border)",
                    marginBottom: 14,
                  }}
                >
                  <Icon name={ic} size={20} />
                </span>
                <h3 style={{ fontSize: "1.15rem", marginBottom: 8 }}>{t}</h3>
                <p
                  className="muted"
                  style={{ fontSize: "0.95rem", lineHeight: 1.55 }}
                >
                  {d}
                </p>
              </div>
            ))}
          </Reveal>

          {/* CTA */}
          <div className="flex center" style={{ gap: 14, flexWrap: "wrap" }}>
            <Button
              variant="primary"
              size="lg"
              icon="whatsapp"
              href={BRAND.whatsappLink}
            >
              Falar com a oficina
            </Button>
            <Link href="/cursos" className="btn btn-secondary btn-lg">
              Ver cursos
              <Icon name="arrow" size={19} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
