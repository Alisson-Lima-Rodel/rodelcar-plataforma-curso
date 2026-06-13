import { jsonLd } from "@/lib/seo";

/** Bloco de dados estruturados (schema.org). A serialização escapa `<`,
 *  então conteúdo do banco não escapa do script (ver lib/seo.ts). */
export function JsonLd({ data }: { data: unknown }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: jsonLd(data) }}
    />
  );
}
