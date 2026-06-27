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
  title: "Contato",
  description:
    "Fale com a RödelCar Câmbios em Canoas-RS: WhatsApp, telefone, e-mail e redes sociais. Diagnóstico de câmbio automático e automatizado sem achismo.",
  alternates: { canonical: "/contato" },
};

// Telefone para link tel: derivado do número do WhatsApp (só dígitos).
const TEL = `+${BRAND.whatsappLink.replace(/\D/g, "")}`;

type Canal = {
  icon: string;
  label: string;
  value: string;
  href: string;
  external?: boolean;
  primary?: boolean;
};

const CANAIS: Canal[] = [
  {
    icon: "whatsapp",
    label: "WhatsApp",
    value: BRAND.whatsapp,
    href: BRAND.whatsappLink,
    external: true,
    primary: true,
  },
  { icon: "phone", label: "Telefone", value: BRAND.whatsapp, href: TEL },
  {
    icon: "mail",
    label: "E-mail",
    value: BRAND.email,
    href: `mailto:${BRAND.email}`,
  },
  {
    icon: "instagram",
    label: "Instagram",
    value: "@rodelcar.cambios",
    href: BRAND.instagram,
    external: true,
  },
  {
    icon: "youtube",
    label: "YouTube",
    value: BRAND.channel,
    href: BRAND.youtube,
    external: true,
  },
  {
    icon: "pin",
    label: "Endereço",
    value: BRAND.address,
    href: BRAND.mapsLink,
    external: true,
  },
];

export default function ContatoPage() {
  const jsonld = {
    "@context": "https://schema.org",
    "@type": "ContactPage",
    "@id": `${SITE_URL}/contato`,
    url: `${SITE_URL}/contato`,
    name: "Contato — RödelCar Câmbios",
    about: { "@id": `${SITE_URL}/#org` },
  };

  return (
    <main>
      <JsonLd data={jsonld} />
      <section className="section">
        <div className="wrap">
          <SectionHead
            eyebrow="Contato"
            title="Fale com a Rödelcar"
            sub="Tire dúvidas sobre diagnóstico, reparo de câmbio ou sobre os cursos. O caminho mais rápido é o WhatsApp — respondemos por lá."
            center
          />

          <Reveal
            className="contato-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: 18,
              maxWidth: 900,
              margin: "0 auto",
            }}
          >
            {CANAIS.map((c) => (
              <a
                key={c.label}
                href={c.href}
                {...(c.external
                  ? { target: "_blank", rel: "noopener noreferrer" }
                  : {})}
                className="card card-hover"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  padding: 20,
                  textDecoration: "none",
                  color: "var(--text)",
                  borderColor: c.primary
                    ? "rgba(229,55,43,0.4)"
                    : "var(--border)",
                }}
              >
                <span
                  style={{
                    flexShrink: 0,
                    width: 46,
                    height: 46,
                    borderRadius: 11,
                    display: "grid",
                    placeItems: "center",
                    background: c.primary
                      ? "var(--primary-soft)"
                      : "var(--surface-2)",
                    color: c.primary ? "var(--primary)" : "var(--text-muted)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <Icon name={c.icon} size={20} />
                </span>
                <span style={{ minWidth: 0 }}>
                  <span
                    className="tag-mono"
                    style={{ display: "block", marginBottom: 3 }}
                  >
                    {c.label}
                  </span>
                  <span
                    style={{
                      fontSize: "0.95rem",
                      fontWeight: 500,
                      lineHeight: 1.35,
                    }}
                  >
                    {c.value}
                  </span>
                </span>
              </a>
            ))}
          </Reveal>

          <div
            className="flex center"
            style={{
              justifyContent: "center",
              gap: 14,
              marginTop: 40,
              flexWrap: "wrap",
            }}
          >
            <Button
              variant="primary"
              size="lg"
              icon="whatsapp"
              href={BRAND.whatsappLink}
            >
              Falar no WhatsApp
            </Button>
            <Link href="/localizacao" className="btn btn-secondary btn-lg">
              <Icon name="pin" size={19} />
              Ver localização
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
