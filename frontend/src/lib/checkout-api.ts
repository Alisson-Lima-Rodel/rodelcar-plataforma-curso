/* Checkout Stripe (hospedado). O backend cria a sessão e devolve `checkout_url`;
   o navegador é redirecionado para a Stripe. Acesso é liberado SÓ pelo webhook.

   Compra sem login: a intenção fica em sessionStorage, o usuário vai para /login
   (entrar OU criar conta) e a compra é retomada automaticamente no sucesso. */

import { ApiError, API_URL, type ApiErrorEnvelope } from "./api";
import { getAccessToken, matricularGratis } from "./auth-api";

export interface CheckoutCriado {
  checkout_url: string;
  session_id: string;
}

/** POST autenticado mínimo (o checkout exige login; sem token nem tenta). */
async function checkoutPost(
  path: string,
  body: unknown,
): Promise<CheckoutCriado> {
  const token = getAccessToken();
  if (!token)
    throw new ApiError(
      401,
      "NAO_AUTENTICADO",
      "Faça login para comprar.",
      null,
    );
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const err = (data as ApiErrorEnvelope | null)?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "ERROR",
      err?.message ?? res.statusText,
      err?.details ?? null,
    );
  }
  return data as CheckoutCriado;
}

export const comprarCurso = (cursoSlug: string) =>
  checkoutPost("/checkout/avulso", { curso_slug: cursoSlug });

export const assinarPlano = (planoId: string) =>
  checkoutPost("/checkout/assinatura-cartao", { plano_id: planoId });

// ── Intenção de compra (sobrevive ao redirect p/ login) ───────────────────────
const INTENT_KEY = "rodelcar_compra_pendente";

export type CompraIntent =
  | { tipo: "curso"; slug: string }
  | { tipo: "plano"; planoId: string }
  | { tipo: "gratis"; slug: string }; // matrícula gratuita (curso grátis)

export function salvarCompraPendente(intent: CompraIntent) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(INTENT_KEY, JSON.stringify(intent));
}

export function lerCompraPendente(): CompraIntent | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(INTENT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CompraIntent;
  } catch {
    return null;
  }
}

export function limparCompraPendente() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(INTENT_KEY);
}

/** Executa a intenção: curso grátis matricula e vai pro player; pago cria a
 *  sessão na Stripe e redireciona. Reusa o mesmo fluxo de resume pós-login. */
export async function executarCompra(intent: CompraIntent): Promise<void> {
  if (intent.tipo === "gratis") {
    await matricularGratis(intent.slug);
    limparCompraPendente();
    window.location.assign(`/curso?slug=${encodeURIComponent(intent.slug)}`);
    return;
  }
  const sessao =
    intent.tipo === "curso"
      ? await comprarCurso(intent.slug)
      : await assinarPlano(intent.planoId);
  limparCompraPendente();
  window.location.assign(sessao.checkout_url);
}

/** Mensagem amigável para erros de checkout (envelope padrão do contrato). */
export function mensagemErroCompra(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === "PRECO_NAO_CONFIGURADO" || e.code === "PLANO_NAO_ENCONTRADO")
      return "Este item está temporariamente indisponível para compra online.";
    if (e.code === "PIX_INDISPONIVEL")
      return "Pix indisponível no momento — tente pagar com cartão.";
    if (e.code === "STRIPE_NAO_CONFIGURADO" || e.code === "STRIPE_ERRO")
      return "Pagamentos temporariamente indisponíveis. Tente novamente em instantes.";
    if (e.code === "RATE_LIMITED")
      return "Muitas tentativas. Aguarde um instante e tente de novo.";
    return e.message;
  }
  return "Não foi possível iniciar a compra. Tente novamente.";
}
