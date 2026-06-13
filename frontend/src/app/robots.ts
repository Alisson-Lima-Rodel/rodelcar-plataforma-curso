import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

/** /robots.txt — libera o portal público e bloqueia as áreas logadas.
 *  O player do LMS fica em "/curso" (singular), que colide no prefixo com
 *  "/cursos" (vitrine pública). Não dá para bloquear um sem o outro com regra
 *  de prefixo portável, então o player é mantido fora do índice pelo
 *  `robots: { index: false }` no metadata do layout (lms) — não aqui. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/admin",
          "/login",
          "/painel",
          "/meus-cursos",
          "/certificado",
          "/sucesso",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
