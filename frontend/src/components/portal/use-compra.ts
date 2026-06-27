"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { getAccessToken } from "@/lib/auth-api";
import {
  type CompraIntent,
  executarCompra,
  mensagemErroCompra,
  salvarCompraPendente,
} from "@/lib/checkout-api";
import { ApiError } from "@/lib/api";
import { usePortal } from "./portal-context";

/** De onde a compra foi iniciada:
 *  - "publico": site público. Mesmo com sessão salva, NÃO compra direto — manda
 *    para /login confirmar quem é o usuário (evita comprar com a conta de outra
 *    pessoa que ficou logada no mesmo navegador).
 *  - "lms": dentro da Área do Aluno (já autenticado/confirmado) → compra direto,
 *    sem novo login. É a única exceção. */
export type CompraContexto = "publico" | "lms";

/** Inicia a compra. No público sempre passa pela confirmação de login; no LMS,
 *  com sessão válida, cria a sessão Stripe e redireciona direto. */
export function useCompra() {
  const router = useRouter();
  const { showToast } = usePortal();
  const [comprando, setComprando] = useState(false);

  const iniciarCompra = async (
    intent: CompraIntent,
    contexto: CompraContexto = "publico",
  ) => {
    if (comprando) return;

    // Público: nunca reutiliza a sessão salva silenciosamente — confirma no login.
    // Sem token (qualquer contexto): também precisa entrar/cadastrar.
    if (contexto === "publico" || !getAccessToken()) {
      salvarCompraPendente(intent);
      router.push("/login?compra=1");
      return;
    }

    setComprando(true);
    try {
      await executarCompra(intent); // redireciona p/ a Stripe em caso de sucesso
    } catch (e) {
      // Sessão expirada → mesmo caminho do não-logado (login retoma a compra).
      if (e instanceof ApiError && e.status === 401) {
        salvarCompraPendente(intent);
        router.push("/login?compra=1");
        return;
      }
      showToast({
        title: "Não foi possível iniciar a compra",
        msg: mensagemErroCompra(e),
      });
      setComprando(false);
    }
  };

  return { iniciarCompra, comprando };
}
