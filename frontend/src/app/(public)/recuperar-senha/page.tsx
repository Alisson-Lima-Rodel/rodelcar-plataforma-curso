import type { Metadata } from "next";
import "../../lms.css";
import { ResetSenha } from "@/components/auth/reset-senha";

export const metadata: Metadata = {
  title: "Redefinir senha",
  robots: { index: false, follow: false },
};

export default function RecuperarSenhaPage() {
  return <ResetSenha />;
}
