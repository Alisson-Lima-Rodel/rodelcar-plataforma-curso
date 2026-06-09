"""Checkout hospedado do Stripe — compra avulsa (cartão + Pix).

Usa o Stripe Checkout HOSPEDADO (escopo PCI mínimo, 3DS automático). O acesso ao
conteúdo é liberado SOMENTE pelo webhook (`/webhooks/pagamento/stripe`), nunca pela
`success_url` (o redirect é só UX e pode ser forjado).
"""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.dependencies import get_current_aluno
from app.models import Aluno, Curso
from app.schemas.pagamentos import CheckoutAvulsoRequest, CheckoutCriado

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checkout", tags=["checkout"])


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


@router.post("/avulso", response_model=CheckoutCriado)
async def checkout_avulso(
    body: CheckoutAvulsoRequest,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    if not settings.STRIPE_SECRET_KEY:
        raise _err(503, "STRIPE_NAO_CONFIGURADO", "Pagamentos indisponíveis no momento.")

    curso = (
        await db.execute(select(Curso).where(Curso.slug == body.curso_slug))
    ).scalar_one_or_none()
    if curso is None:
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    if not curso.stripe_price_id:
        raise _err(404, "PRECO_NAO_CONFIGURADO", "Curso sem preço configurado no Stripe.")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Garante (ou reutiliza) o Customer do Stripe ligado ao aluno.
    customer_id = aluno.stripe_customer_id
    if not customer_id:
        try:
            customer = await run_in_threadpool(
                stripe.Customer.create,
                email=aluno.email,
                name=aluno.nome,
                metadata={"app_user_id": str(aluno.id)},
            )
        except stripe.error.StripeError:
            logger.exception("Erro ao criar customer no Stripe")
            raise _err(502, "STRIPE_ERRO", "Falha ao criar cliente no Stripe.")
        customer_id = customer.id
        aluno.stripe_customer_id = customer_id
        await db.commit()

    try:
        session = await run_in_threadpool(
            stripe.checkout.Session.create,
            mode="payment",
            customer=customer_id,
            line_items=[{"price": curso.stripe_price_id, "quantity": 1}],
            payment_method_types=["card", "pix"],
            metadata={"app_user_id": str(aluno.id), "curso_slug": curso.slug},
            success_url=settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
    except stripe.error.InvalidRequestError as exc:
        # Pix para conta BR na Stripe pode ser invite-only → mensagem clara.
        msg = str(getattr(exc, "user_message", "") or exc).lower()
        if "pix" in msg:
            raise _err(
                400, "PIX_INDISPONIVEL",
                "Pix indisponível para esta conta Stripe. Tente pagar com cartão.",
            )
        logger.exception("Requisição inválida ao criar a sessão de checkout")
        raise _err(400, "STRIPE_ERRO", "Não foi possível criar a sessão de checkout.")
    except stripe.error.StripeError:
        logger.exception("Erro do Stripe ao criar a sessão de checkout")
        raise _err(502, "STRIPE_ERRO", "Falha ao criar a sessão de checkout.")

    return CheckoutCriado(checkout_url=session.url, session_id=session.id)
