"""Checkout hospedado do Stripe — avulso (cartão+Pix) e assinaturas (cartão / Pix Automático).

Usa o Stripe Checkout HOSPEDADO (escopo PCI mínimo, 3DS automático). O acesso ao
conteúdo é liberado SOMENTE pelo webhook (`/webhooks/pagamento/stripe`), nunca pela
`success_url` (o redirect é só UX e pode ser forjado).
"""

import logging
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.dependencies import get_current_aluno
from app.models import Aluno, Curso, PlanoAssinatura
from app.schemas.pagamentos import (
    CheckoutAssinaturaRequest,
    CheckoutAvulsoRequest,
    CheckoutCriado,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checkout", tags=["checkout"])

# Teto do mandato do Pix Automático = 2× o valor do plano (cobre IOF e upgrades).
_PIX_MANDATE_MULT = 2


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


def _exige_stripe() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise _err(503, "STRIPE_NAO_CONFIGURADO", "Pagamentos indisponíveis no momento.")
    stripe.api_key = settings.STRIPE_SECRET_KEY


async def _ensure_customer(db: AsyncSession, aluno: Aluno) -> str:
    """Reaproveita ou cria o Customer do Stripe ligado ao aluno (persistindo o id)."""
    if aluno.stripe_customer_id:
        return aluno.stripe_customer_id
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
    aluno.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


def _tratar_erro_stripe(exc: Exception) -> HTTPException:
    """Mapeia erros do Stripe para o envelope padrão (Pix invite-only → claro)."""
    if isinstance(exc, stripe.error.InvalidRequestError):
        msg = str(getattr(exc, "user_message", "") or exc).lower()
        if "pix" in msg:
            return _err(
                400, "PIX_INDISPONIVEL",
                "Pix indisponível para esta conta Stripe. Tente pagar com cartão.",
            )
        logger.exception("Requisição inválida ao criar a sessão de checkout")
        return _err(400, "STRIPE_ERRO", "Não foi possível criar a sessão de checkout.")
    logger.exception("Erro do Stripe ao criar a sessão de checkout")
    return _err(502, "STRIPE_ERRO", "Falha ao criar a sessão de checkout.")


@router.post("/avulso", response_model=CheckoutCriado)
async def checkout_avulso(
    body: CheckoutAvulsoRequest,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    _exige_stripe()
    curso = (
        await db.execute(select(Curso).where(Curso.slug == body.curso_slug))
    ).scalar_one_or_none()
    if curso is None:
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    if not curso.stripe_price_id:
        raise _err(404, "PRECO_NAO_CONFIGURADO", "Curso sem preço configurado no Stripe.")

    customer_id = await _ensure_customer(db, aluno)
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
    except stripe.error.StripeError as exc:
        raise _tratar_erro_stripe(exc)

    return CheckoutCriado(checkout_url=session.url, session_id=session.id)


async def _resolver_plano(db: AsyncSession, plano_id) -> PlanoAssinatura:
    plano = (
        await db.execute(select(PlanoAssinatura).where(PlanoAssinatura.id == plano_id))
    ).scalar_one_or_none()
    if plano is None or plano.status != "Ativo":
        raise _err(404, "PLANO_NAO_ENCONTRADO", "Plano de assinatura não encontrado.")
    if not plano.stripe_price_id:
        raise _err(404, "PRECO_NAO_CONFIGURADO", "Plano sem preço configurado no Stripe.")
    return plano


@router.post("/assinatura-cartao", response_model=CheckoutCriado)
async def checkout_assinatura_cartao(
    body: CheckoutAssinaturaRequest,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    _exige_stripe()
    plano = await _resolver_plano(db, body.plano_id)
    customer_id = await _ensure_customer(db, aluno)
    try:
        session = await run_in_threadpool(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": plano.stripe_price_id, "quantity": 1}],
            payment_method_types=["card"],
            metadata={"app_user_id": str(aluno.id), "plano_id": str(plano.id)},
            subscription_data={"metadata": {"app_user_id": str(aluno.id)}},
            success_url=settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
    except stripe.error.StripeError as exc:
        raise _tratar_erro_stripe(exc)

    return CheckoutCriado(checkout_url=session.url, session_id=session.id)


@router.post("/assinatura-pix", response_model=CheckoutCriado)
async def checkout_assinatura_pix(
    body: CheckoutAssinaturaRequest,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    _exige_stripe()
    plano = await _resolver_plano(db, body.plano_id)
    customer_id = await _ensure_customer(db, aluno)

    # Teto do mandato (amount_type=maximum) = 2× o valor do plano, em centavos.
    teto = int((Decimal(str(plano.preco)) * 100 * _PIX_MANDATE_MULT).to_integral_value())
    try:
        session = await run_in_threadpool(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": plano.stripe_price_id, "quantity": 1}],
            payment_method_types=["pix"],
            payment_method_options={
                "pix": {
                    "mandate_options": {
                        "amount": teto,
                        "amount_type": "maximum",
                        "payment_schedule": "monthly",
                        "reference": f"RodelCar {plano.nome}"[:80],
                    }
                }
            },
            metadata={"app_user_id": str(aluno.id), "plano_id": str(plano.id)},
            subscription_data={"metadata": {"app_user_id": str(aluno.id)}},
            success_url=settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
    except stripe.error.StripeError as exc:
        raise _tratar_erro_stripe(exc)

    return CheckoutCriado(checkout_url=session.url, session_id=session.id)
