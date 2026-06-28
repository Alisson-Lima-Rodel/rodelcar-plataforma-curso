import type { Metadata } from "next";
import { AllCourses } from "@/components/portal/all-courses";
import { JsonLd } from "@/components/seo/json-ld";
import { getCursos, getPlanos } from "@/lib/api";
import { SITE_URL } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Todos os cursos",
  description:
    "Catálogo completo de cursos de câmbio automático e automatizado da RödelCar: Dualogic, PowerShift, iMotion, Easytronic, DSG e automático convencional.",
  alternates: { canonical: "/cursos" },
};

export default async function CursosPage() {
  const [courses, planos] = await Promise.all([getCursos(), getPlanos()]);
  const lista = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: courses.map((c, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: c.title,
      url: `${SITE_URL}/cursos/${encodeURIComponent(c.id)}`,
    })),
  };
  return (
    <main>
      <JsonLd data={lista} />
      <AllCourses courses={courses} planos={planos} />
    </main>
  );
}
