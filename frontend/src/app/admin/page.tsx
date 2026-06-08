import type { Metadata } from "next";
import "../lms.css";
import "../admin.css";
import { AdminApp } from "@/components/admin/admin-app";
import { AdminProvider } from "@/components/providers/admin-provider";

export const metadata: Metadata = {
  title: "Painel Administrador",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  return (
    <AdminProvider>
      <AdminApp />
    </AdminProvider>
  );
}
