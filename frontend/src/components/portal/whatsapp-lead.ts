"use client";

import { useMutation } from "@tanstack/react-query";
import { createLead, type LeadInput } from "@/lib/api";
import { BRAND } from "@/lib/portal-data";

/** Telefone BR: aceita máscara/“+55”; válido com 10–11 dígitos (DDD + número). */
export function telefoneValidoBR(v: string): boolean {
  const d = v.replace(/\D/g, "").replace(/^55(?=\d{10,11}$)/, "");
  return d.length === 10 || d.length === 11;
}

/** Abre o WhatsApp da oficina (+55 51 9574-0655) com a mensagem pré-preenchida,
 *  em nova aba. Precisa rodar no gesto do clique p/ não ser bloqueado. */
export function abrirWhatsApp(texto: string): void {
  if (typeof window === "undefined") return;
  window.open(
    `${BRAND.whatsappLink}?text=${encodeURIComponent(texto)}`,
    "_blank",
    "noopener,noreferrer",
  );
}

/** Registra o lead no banco (best-effort) E abre o WhatsApp da oficina. O
 *  `window.open` roda síncrono no clique (evita bloqueio de pop-up); o registro
 *  do lead é disparado em seguida. `onDone` fecha o diálogo ao concluir. */
export function useLeadWhatsapp(onDone: () => void) {
  const mutation = useMutation({
    mutationFn: createLead,
    onSettled: onDone, // o WhatsApp já abriu; sucesso ou falha do registro fecha
  });
  const enviar = (lead: LeadInput, texto: string) => {
    if (mutation.isPending) return;
    abrirWhatsApp(texto);
    mutation.mutate(lead);
  };
  return { enviar, enviando: mutation.isPending };
}
