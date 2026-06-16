/** @type {import('next').NextConfig} */

const isDev = process.env.NODE_ENV !== "production";

// Origem da API (NEXT_PUBLIC_API_URL) extraída p/ liberar no connect-src — é o
// único host externo que o front consulta via fetch. Fallback p/ localhost em dev.
const apiOrigin = (() => {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_URL ?? "").origin;
  } catch {
    return isDev ? "http://localhost:8000" : "";
  }
})();

// CSP ENFORCE do front (o site serve HTML/JS ao usuário; o backend tem o seu p/ a API).
// Calibrado p/ não quebrar: Stripe Checkout, player Panda Video, thumbnails do YouTube,
// fontes auto-hospedadas (next/font) e a hidratação inline do App Router.
const csp = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'", // reforça o X-Frame-Options
  "form-action 'self' https://checkout.stripe.com",
  // Next 14 injeta hidratação inline (sem nonce) → 'unsafe-inline'. Em dev o HMR usa eval.
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:", // thumbnails de curso vêm de CDN/Supabase arbitrário
  "font-src 'self'", // next/font auto-hospeda no build
  "frame-src 'self' https://checkout.stripe.com https://*.tv.pandavideo.com.br",
  `connect-src 'self'${apiOrigin ? " " + apiOrigin : ""}${
    isDev ? " ws: http://localhost:*" : ""
  }`,
  "manifest-src 'self'",
  "media-src 'self' blob: https://*.tv.pandavideo.com.br",
  "upgrade-insecure-requests",
].join("; ");

// Headers de segurança do front (o backend já põe os dele em toda resposta da API).
const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
  // HSTS é ignorado sob HTTP (dev/localhost), então é seguro enviar sempre.
  {
    key: "Strict-Transport-Security",
    value: "max-age=31536000; includeSubDomains",
  },
];

const nextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
