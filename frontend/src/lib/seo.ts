/* Constantes e utilitários de SEO. Tudo que os buscadores leem nasce aqui:
   URL canônica do site e serialização segura de JSON-LD. */

export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://rodelcar.com.br";

export const SITE_NAME = "RödelCar";

/** Serializa JSON-LD escapando `<` para que conteúdo vindo do banco nunca
 *  feche o `</script>` (o JSON segue válido: < é escape padrão). */
export function jsonLd(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

/** A oficina como entidade (schema.org/AutoRepair) — referenciada pelo
 *  WebSite e como `provider` dos cursos. */
export const ORG_JSONLD = {
  "@context": "https://schema.org",
  "@type": "AutoRepair",
  "@id": `${SITE_URL}/#org`,
  name: "RödelCar Câmbios",
  url: SITE_URL,
  logo: `${SITE_URL}/icons/icon-512.png`,
  description:
    "Especialista em câmbio automático e automatizado em Canoas-RS: " +
    "Dualogic, PowerShift, iMotion, Easytronic e DSG. Diagnóstico de " +
    "bancada e cursos para mecânicos.",
  areaServed: "Canoas e região metropolitana de Porto Alegre",
  address: {
    "@type": "PostalAddress",
    addressLocality: "Canoas",
    addressRegion: "RS",
    addressCountry: "BR",
  },
  knowsAbout: [
    "câmbio automático",
    "câmbio automatizado",
    "Dualogic",
    "PowerShift",
    "DSG",
    "iMotion",
    "Easytronic",
  ],
};

export const WEBSITE_JSONLD = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": `${SITE_URL}/#website`,
  url: SITE_URL,
  name: SITE_NAME,
  inLanguage: "pt-BR",
  publisher: { "@id": `${SITE_URL}/#org` },
};
