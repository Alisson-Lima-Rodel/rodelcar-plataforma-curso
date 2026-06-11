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

/** Inicia a compra: logado → cria a sessão Stripe e redireciona; sem login →
 * guarda a intenção e manda para /login (entrar ou criar conta), que retoma. */
export function useCompra() {
  const router = useRouter();
  const { showToast } = usePortal();
  const [comprando, setComprando] = useState(false);

  const iniciarCompra = async (intent: CompraIntent) => {
    if (comprando) return;

    if (!getAccessToken()) {
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
