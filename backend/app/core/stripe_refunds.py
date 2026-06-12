"""Estorno e cancelamento de assinatura na Stripe (direito de arrependimento).

CDC art. 49: até GARANTIA_DIAS após a compra o aluno pode cancelar com reembolso
integral. O reembolso é do PaymentIntent; para assinaturas, o PI é resolvido a
partir da invoice (API 2025+ usa /v1/invoice_payments; legado tinha o campo
`payment_intent` direto na invoice — os dois caminhos são suportados).
"""

import logging
from datetime import datetime, timedelta, timezone

import stripe
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Matricula, Pagamento, StatusMatricula, StatusPagamento

logger = logging.getLogger(__name__)

GARANTIA_DIAS = 7


def limite_cancelamento(pag: Pagamento | None) -> datetime | None:
    """Fim da janela de arrependimento do ALUNO: 7 dias após o pagamento aprovado.

    O admin não está sujeito à janela (reembolso de cortesia a qualquer tempo).
    """
    if pag is None or pag.status != StatusPagamento.aprovado or pag.gateway != "stripe":
        return None
    criado = pag.criado_em if pag.criado_em.tzinfo else pag.criado_em.replace(tzinfo=timezone.utc)
    return criado + timedelta(days=GARANTIA_DIAS)


async def executar_cancelamento(
    db: AsyncSession, mat: Matricula, pag: Pagamento
) -> tuple[bool, int]:
    """Estorna na Stripe e revoga o(s) acesso(s). Retorna (assinatura_cancelada,
    cursos_revogados). Stripe PRIMEIRO (exceção → nada muda no banco); quem
    chama trata StripeError e commita.
    """
    if mat.stripe_subscription_id:
        pi = await payment_intent_da_invoice(pag.gateway_transaction_id)
        if pi:
            await reembolsar_payment_intent(pi)
        await cancelar_assinatura_stripe(mat.stripe_subscription_id)
        mats_sub = (
            await db.execute(
                select(Matricula).where(
                    Matricula.stripe_subscription_id == mat.stripe_subscription_id
                )
            )
        ).scalars().all()
        for m in mats_sub:
            m.status = StatusMatricula.expirado
        pag.status = StatusPagamento.estornado
        return True, len(mats_sub)

    await reembolsar_payment_intent(pag.gateway_transaction_id)
    mat.status = StatusMatricula.expirado
    pag.status = StatusPagamento.estornado
    return False, 1


async def reembolsar_payment_intent(pi_id: str) -> str | None:
    """Reembolso integral do PaymentIntent. Retorna o id do refund.

    Já reembolsado (retentativa após falha parcial) conta como sucesso — o
    objetivo (dinheiro de volta) já foi atingido.
    """
    try:
        refund = await run_in_threadpool(stripe.Refund.create, payment_intent=pi_id)
        return refund.id
    except stripe.error.InvalidRequestError as exc:
        if "already been refunded" in str(exc).lower():
            logger.info("PaymentIntent %s já reembolsado — seguindo.", pi_id)
            return None
        raise


async def payment_intent_da_invoice(invoice_id: str) -> str | None:
    """PaymentIntent que pagou a invoice (assinatura)."""
    pagamentos = await run_in_threadpool(stripe.InvoicePayment.list, invoice=invoice_id)
    for ip in pagamentos.get("data", []):
        pagamento = ip.get("payment") or {}
        if pagamento.get("payment_intent"):
            return pagamento["payment_intent"]
    # API legada: o campo vinha direto na invoice.
    invoice = await run_in_threadpool(stripe.Invoice.retrieve, invoice_id)
    return invoice.get("payment_intent")


async def cancelar_assinatura_stripe(sub_id: str) -> None:
    """Cancela a assinatura imediatamente (sem cobranças futuras).

    Já cancelada (retentativa) conta como sucesso.
    """
    try:
        await run_in_threadpool(stripe.Subscription.cancel, sub_id)
    except stripe.error.InvalidRequestError as exc:
        if "canceled subscription" in str(exc).lower():
            logger.info("Assinatura %s já cancelada — seguindo.", sub_id)
            return
        raise
