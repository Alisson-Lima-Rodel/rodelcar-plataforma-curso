import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CourseDetail } from "@/components/portal/course-detail";
import { COURSES, getCourse } from "@/lib/portal-data";

interface Params {
  params: { slug: string };
}

export function generateStaticParams() {
  return COURSES.map((c) => ({ slug: c.id }));
}

export function generateMetadata({ params }: Params): Metadata {
  const course = getCourse(params.slug);
  if (!course) return { title: "Curso não encontrado" };
  return {
    title: course.title,
    description: course.desc ?? course.tagline,
    openGraph: {
      title: course.title,
      description: course.tagline,
    },
  };
}

export default function CoursePage({ params }: Params) {
  const course = getCourse(params.slug);
  if (!course) notFound();
  return (
    <main>
      <CourseDetail course={course} />
    </main>
  );
}
