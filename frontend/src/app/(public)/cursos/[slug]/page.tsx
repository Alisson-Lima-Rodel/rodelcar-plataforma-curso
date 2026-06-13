import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CourseDetail } from "@/components/portal/course-detail";
import { JsonLd } from "@/components/seo/json-ld";
import { getAvaliacoes, getCurso, getFaq } from "@/lib/api";
import { SITE_URL } from "@/lib/seo";

interface Params {
  params: { slug: string };
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const course = await getCurso(params.slug);
  if (!course) return { title: "Curso não encontrado" };
  const canonical = `/cursos/${encodeURIComponent(params.slug)}`;
  return {
    title: course.title,
    description: course.desc ?? course.tagline,
    alternates: { canonical },
    openGraph: {
      title: course.title,
      description: course.tagline,
      url: canonical,
      // Capa do curso como og:image; sem capa, herda a OG padrão do site.
      images: course.cover
        ? [{ url: course.cover, alt: course.title }]
        : undefined,
    },
  };
}

/** Carga horária no formato ISO 8601 exigido pelo schema.org ("10h" → PT10H). */
function cargaHoraria(horas: string): string | null {
  const m = horas.match(/(\d+)/);
  return m ? `PT${m[1]}H` : null;
}

export default async function CoursePage({ params }: Params) {
  const [course, faqs, avaliacoes] = await Promise.all([
    getCurso(params.slug),
    getFaq(),
    getAvaliacoes(params.slug),
  ]);
  if (!course) notFound();

  const url = `${SITE_URL}/cursos/${encodeURIComponent(params.slug)}`;
  const carga = cargaHoraria(course.hours);
  const cursoLd = {
    "@context": "https://schema.org",
    "@type": "Course",
    name: course.title,
    description: course.desc ?? course.tagline,
    url,
    inLanguage: "pt-BR",
    ...(course.cover ? { image: course.cover } : {}),
    provider: { "@id": `${SITE_URL}/#org` },
    offers: {
      "@type": "Offer",
      price: course.price.toFixed(2),
      priceCurrency: "BRL",
      availability: "https://schema.org/InStock",
      url,
      category: "Paid",
    },
    ...(carga
      ? {
          hasCourseInstance: [
            {
              "@type": "CourseInstance",
              courseMode: "Online",
              courseWorkload: carga,
            },
          ],
        }
      : {}),
    // aggregateRating só sai com avaliação real (Google rejeita vazio) → estrelas
    // do resultado de busca aparecem quando há reviews aprovadas.
    ...(avaliacoes.total > 0 && avaliacoes.media
      ? {
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: avaliacoes.media,
            reviewCount: avaliacoes.total,
            bestRating: 5,
            worstRating: 1,
          },
        }
      : {}),
  };
  const trilha = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Início", item: SITE_URL },
      {
        "@type": "ListItem",
        position: 2,
        name: "Cursos",
        item: `${SITE_URL}/cursos`,
      },
      { "@type": "ListItem", position: 3, name: course.title, item: url },
    ],
  };
  const faqLd = faqs.length
    ? {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: faqs.map((f) => ({
          "@type": "Question",
          name: f.q,
          acceptedAnswer: { "@type": "Answer", text: f.a },
        })),
      }
    : null;

  return (
    <main>
      <JsonLd data={cursoLd} />
      <JsonLd data={trilha} />
      {faqLd && <JsonLd data={faqLd} />}
      <CourseDetail course={course} faqs={faqs} avaliacoes={avaliacoes} />
    </main>
  );
}
