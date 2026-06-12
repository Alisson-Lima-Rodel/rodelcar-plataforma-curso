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

from app.models import (
    Aula,
    Matricula,
    Modulo,
    Pagamento,
    Progresso,
    StatusMatricula,
    StatusPagamento,
)

logger = logging.getLogger(__name__)

GARANTIA_DIAS = 7

# Anti-abuso do AUTOATENDIMENTO (o suporte/admin não tem essas travas):
# - consumo alto do curso não é "arrependimento" — é uso;
# - estornos repetidos na conta indicam o loop compra→assiste→reembolsa.
# Nesses casos o aluno é direcionado ao suporte, que decide caso a caso.
LIMITE_PROGRESSO_REEMBOLSO = 20.0  # % máximo assistido p/ cancelar sozinho
LIMITE_REEMBOLSOS_AUTO = 2         # nº de estornos na conta que trava o autoatendimento


def limite_cancelamento(pag: Pagamento | None) -> datetime | None:
    """Fim da janela de arrependimento do ALUNO: 7 dias após o pagamento aprovado.

    O admin não está sujeito à janela (reembolso de cortesia a qualquer tempo).
    """
    if pag is None or pag.status != StatusPagamento.aprovado or pag.gateway != "stripe":
        return None
    criado = pag.criado_em if pag.criado_em.tzinfo else pag.criado_em.replace(tzinfo=timezone.utc)
    return criado + timedelta(days=GARANTIA_DIAS)


def motivo_bloqueio_autoatendimento(progresso_pct: float, n_estornos: int) -> str | None:
    """Por que o ALUNO não pode cancelar SOZINHO (None = liberado).

    Anti-abuso do loop comprar→assistir→reembolsar→recomprar. NÃO se aplica ao
    suporte/admin (que reembolsa por cortesia a qualquer tempo via /admin/reembolsos):
    - progresso acima do teto = consumiu o conteúdo, não é arrependimento;
    - estornos demais na conta = padrão de abuso → vai para análise do suporte.
    """
    if progresso_pct > LIMITE_PROGRESSO_REEMBOLSO:
        return "RECURSO_CONSUMIDO"
    if n_estornos >= LIMITE_REEMBOLSOS_AUTO:
        return "LIMITE_REEMBOLSOS"
    return None


async def contar_estornos(db: AsyncSession, aluno_id) -> int:
    """Nº de pagamentos já estornados na conta (cada reembolso = 1)."""
    from sqlalchemy import func

    return (
        await db.scalar(
            select(func.count())
            .select_from(Pagamento)
            .where(
                Pagamento.aluno_id == aluno_id,
                Pagamento.status == StatusPagamento.estornado,
            )
        )
    ) or 0


async def progresso_para_gate(db: AsyncSession, mat: Matricula) -> float:
    """% assistido relevante p/ o gate. Avulso = o próprio curso; assinatura =
    o MAIOR progresso entre os cursos da assinatura (cancelar 1 revoga todos)."""
    from sqlalchemy import func

    if mat.stripe_subscription_id:
        alvos = (
            await db.execute(
                select(Matricula).where(
                    Matricula.stripe_subscription_id == mat.stripe_subscription_id
                )
            )
        ).scalars().all()
    else:
        alvos = [mat]

    curso_ids = list({m.curso_id for m in alvos})
    contagens = {
        row.curso_id: row.n
        for row in (
            await db.execute(
                select(Modulo.curso_id, func.count(Aula.id).label("n"))
                .join(Aula, Aula.modulo_id == Modulo.id)
                .where(Modulo.curso_id.in_(curso_ids))
                .group_by(Modulo.curso_id)
            )
        ).all()
    }
    mat_ids = [m.id for m in alvos]
    somas: dict = {}
    rows = (
        await db.execute(
            select(Progresso.matricula_id, func.sum(Progresso.percentual).label("s"))
            .where(Progresso.matricula_id.in_(mat_ids))
            .group_by(Progresso.matricula_id)
        )
    ).all()
    for r in rows:
        somas[r.matricula_id] = float(r.s or 0)

    maior = 0.0
    for m in alvos:
        total = contagens.get(m.curso_id, 0)
        if total:
            maior = max(maior, round(somas.get(m.id, 0.0) / total, 2))
    return maior


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
