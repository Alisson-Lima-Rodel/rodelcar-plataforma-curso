import { AllCourses } from "@/components/portal/all-courses";
import { getCursos, getPlanos } from "@/lib/api";

/** Catálogo dentro da Área do Aluno (item 6.1): o aluno sem curso vigente vê e
 *  compra sem sair do LMS. Contexto "lms" → compra direto, sem pedir login de
 *  novo (exceção do item 6.2). */
export default async function CatalogoLmsPage() {
  const [courses, planos] = await Promise.all([getCursos(), getPlanos()]);
  return (
    <AllCourses courses={courses} planos={planos} contexto="lms" />
  );
}
