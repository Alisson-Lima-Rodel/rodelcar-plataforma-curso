import type { Metadata } from "next";
import { AllCourses } from "@/components/portal/all-courses";

export const metadata: Metadata = {
  title: "Todos os cursos",
  description:
    "Catálogo completo de cursos de câmbio automático e automatizado da RödelCar: Dualogic, PowerShift, iMotion, Easytronic, DSG e automático convencional.",
};

export default function CursosPage() {
  return (
    <main>
      <AllCourses />
    </main>
  );
}
