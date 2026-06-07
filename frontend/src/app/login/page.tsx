import type { Metadata } from "next";
import "../lms.css";
import { Login } from "@/components/auth/login";

export const metadata: Metadata = {
  title: "Entrar",
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return <Login />;
}
