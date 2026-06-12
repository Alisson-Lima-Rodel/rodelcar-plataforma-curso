import type { Metadata } from "next";
import { MyCourses } from "@/components/lms/my-courses";

export const metadata: Metadata = { title: "Meus cursos" };

export default function MeusCursosPage() {
  return <MyCourses />;
}
