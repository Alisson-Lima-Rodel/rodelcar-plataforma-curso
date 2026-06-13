import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

/** /robots.txt — libera o portal público e bloqueia as áreas logadas.
 *  Atenção ao prefixo: "/curso$" e "/curso?" miram só o player do LMS
 *  (singular) sem derrubar "/cursos" (vitrine pública). */
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
          "/curso$",
          "/curso?",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
