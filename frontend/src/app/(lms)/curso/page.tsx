import type { Metadata } from "next";
import { Player } from "@/components/lms/player";

export const metadata: Metadata = { title: "Aula em andamento" };

export default function CursoPage() {
  return <Player />;
}
