"use client";

import dynamic from "next/dynamic";
import { AdminProvider } from "@/components/providers/admin-provider";

// Painel 100% logado e `noindex`: não há valor em renderizá-lo no servidor.
// `ssr: false` tira o AdminApp do SSR. O `loading` é `null` de propósito: assim o
// servidor NÃO emite nenhuma marcação do painel (nem a tela de "Carregando"),
// logo o React não HIDRATA nada aqui — o que elimina os erros de "hydration
// mismatch" mesmo quando uma extensão do navegador / tradução automática mexe no
// DOM antes da hidratação. A própria AdminApp mostra "Carregando…" (render só no
// cliente) enquanto confere a sessão, então a UX do loader é preservada.
const AdminApp = dynamic(
  () => import("@/components/admin/admin-app").then((m) => m.AdminApp),
  { ssr: false, loading: () => null },
);

export function AdminClient() {
  return (
    <AdminProvider>
      <AdminApp />
    </AdminProvider>
  );
}
