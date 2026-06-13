import type { MetadataRoute } from "next";
import { getCursos } from "@/lib/api";
import { SITE_URL } from "@/lib/seo";

/** /sitemap.xml — home, vitrine e cada página de venda de curso (slugs vêm
 *  do backend; se a API estiver fora, sai só com as rotas fixas). */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const cursos = await getCursos();
  const agora = new Date();
  return [
    {
      url: SITE_URL,
      lastModified: agora,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/cursos`,
      lastModified: agora,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    ...cursos.map((c) => ({
      url: `${SITE_URL}/cursos/${encodeURIComponent(c.id)}`,
      lastModified: agora,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
  ];
}
