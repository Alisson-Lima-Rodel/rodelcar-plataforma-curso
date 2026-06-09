import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CourseDetail } from "@/components/portal/course-detail";
import { getCurso, getFaq } from "@/lib/api";

interface Params {
  params: { slug: string };
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const course = await getCurso(params.slug);
  if (!course) return { title: "Curso não encontrado" };
  return {
    title: course.title,
    description: course.desc ?? course.tagline,
    openGraph: { title: course.title, description: course.tagline },
  };
}

export default async function CoursePage({ params }: Params) {
  const [course, faqs] = await Promise.all([getCurso(params.slug), getFaq()]);
  if (!course) notFound();
  return (
    <main>
      <CourseDetail course={course} faqs={faqs} />
    </main>
  );
}
