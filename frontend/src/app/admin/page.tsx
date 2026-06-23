import type { Metadata } from "next";
import "../lms.css";
import "../admin.css";
import { AdminClient } from "@/components/admin/admin-client";

export const metadata: Metadata = {
  title: "Painel Administrador",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  // AdminClient renderiza o painel client-only (ssr:false) — ver admin-client.tsx.
  return <AdminClient />;
}
