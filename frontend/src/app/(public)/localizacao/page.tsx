import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/reveal";
import { SectionHead } from "@/components/ui/section-head";
import { JsonLd } from "@/components/seo/json-ld";
import { BRAND } from "@/lib/portal-data";
import { SITE_URL } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Localização",
  description:
    "Onde fica a RödelCar Câmbios: Rua Esperança, 521 · Estância Velha · Canoas-RS. Veja o mapa, trace a rota e fale com a oficina pelo WhatsApp.",
  alternates: { canonical: "/localizacao" },
};

// Consulta usada tanto no botão "Como chegar" quanto no mapa incorporado.
const MAPS_QUERY =
  "RödelCar Câmbios, Rua Esperança 521, Estância Velha, Canoas - RS, 92030-500";
// Endpoint OFICIAL de embed do Google (o mesmo do "Compartilhar → Incorporar"),
// keyless. Apontamos direto para /maps/embed em vez de ?output=embed porque este
// faz um 301 com `X-Frame-Options: SAMEORIGIN` que o navegador bloqueia no iframe.
// O formato `pb=!1m2!2m1!1s<consulta>` é a variante "busca por texto" (sem coords).
const MAPS_EMBED = `https://www.google.com/maps/embed?origin=mfe&pb=!1m2!2m1!1s${encodeURIComponent(
  MAPS_QUERY,
)
  .replace(/%20/g, "+")
  .replace(/%2C/g, ",")}`;

export default function LocalizacaoPage() {
  const jsonld = {
    "@context": "https://schema.org",
    "@type": "AutoRepair",
    "@id": `${SITE_URL}/#org`,
    name: "RödelCar Câmbios",
    url: `${SITE_URL}/localizacao`,
    telephone: BRAND.whatsapp,
    email: BRAND.email,
    address: {
      "@type": "PostalAddress",
      streetAddress: "Rua Esperança, 521 - Estância Velha",
      addressLocality: "Canoas",
      addressRegion: "RS",
      postalCode: "92030-500",
      addressCountry: "BR",
    },
  };

  return (
    <main>
      <JsonLd data={jsonld} />
      <section className="section">
        <div className="wrap">
          <SectionHead
            eyebrow="Localização"
            title="Onde estamos"
            sub="A oficina fica em Canoas-RS, na região metropolitana de Porto Alegre. Atendemos com hora marcada — agende pelo WhatsApp antes de vir."
          />

          <Reveal
            className="local-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "0.9fr 1.1fr",
              gap: 28,
              alignItems: "stretch",
            }}
          >
            {/* Endereço + ações */}
            <div
              className="card"
              style={{
                padding: 28,
                display: "flex",
                flexDirection: "column",
                gap: 20,
              }}
            >
              <div className="flex center gap-3">
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
                  }}
                >
                  <Icon name="pin" size={20} />
                </span>
                <div>
                  <span className="tag-mono" style={{ display: "block" }}>
                    Endereço
                  </span>
                  <strong style={{ fontSize: "1.05rem" }}>
                    RödelCar Câmbios
                  </strong>
                </div>
              </div>

              <p
                className="muted"
                style={{ fontSize: "1rem", lineHeight: 1.6 }}
              >
                {BRAND.address}
              </p>

              <div
                className="flex center gap-3"
                style={{ flexWrap: "wrap", marginTop: "auto" }}
              >
                <Button variant="primary" icon="pin" href={BRAND.mapsLink}>
                  Como chegar
                </Button>
                <Button
                  variant="secondary"
                  icon="whatsapp"
                  href={BRAND.whatsappLink}
                >
                  Falar com a oficina
                </Button>
              </div>

              <Link
                href="/contato"
                className="btn btn-link"
                style={{ alignSelf: "flex-start" }}
              >
                Ver todos os contatos
                <Icon name="arrow" size={17} />
              </Link>
            </div>

            {/* Mapa incorporado */}
            <div
              className="card"
              style={{
                overflow: "hidden",
                minHeight: 340,
                padding: 0,
              }}
            >
              <iframe
                title="Mapa — RödelCar Câmbios em Canoas-RS"
                src={MAPS_EMBED}
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                style={{
                  width: "100%",
                  height: "100%",
                  border: 0,
                  minHeight: 340,
                }}
              />
            </div>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
