import type { Metadata } from "next";
import { Dashboard } from "@/components/lms/dashboard";

export const metadata: Metadata = { title: "Painel do aluno" };

export default function PainelPage() {
  return <Dashboard />;
}
