"""Checkout hospedado do Stripe — avulso (cartão+Pix) e assinaturas (cartão / Pix Automático).

Usa o Stripe Checkout HOSPEDADO (escopo PCI mínimo, 3DS automático). O acesso ao
conteúdo é liberado SOMENTE pelo webhook (`/webhooks/pagamento/stripe`), nunca pela
`success_url` (o redirect é só UX e pode ser forjado).
"""

import logging
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import limiter
from app.dependencies import get_current_aluno
from app.models import Aluno, Curso, Matricula, PlanoAssinatura, StatusMatricula
from app.schemas.pagamentos import (
    CheckoutAssinaturaRequest,
    CheckoutAvulsoRequest,
    CheckoutCriado,
    StatusCompra,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checkout", tags=["checkout"])

# Timeout de 15s nas chamadas ao Stripe (o default do SDK é 80s). Evita segurar
# threads do pool de `run_in_threadpool` sob degradação da API. Cliente síncrono.
try:  # pragma: no cover - depende do http client disponível no ambiente
    stripe.default_http_client = stripe.http_client.new_default_http_client(timeout=15)
except Exception:
    logger.warning("Não foi possível configurar timeout do http client do Stripe.")

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
@limiter.limit("10/minute")
async def checkout_avulso(
    request: Request,
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

    # Anti-duplicidade: já tem o curso (matrícula ativa) → não abre nova cobrança.
    # Sem isso, o aluno consegue pagar o MESMO curso várias vezes (dupla cobrança).
    if await db.scalar(
        select(Matricula.id).where(
            Matricula.aluno_id == aluno.id,
            Matricula.curso_id == curso.id,
            Matricula.status == StatusMatricula.ativo,
        )
    ):
        raise _err(409, "JA_MATRICULADO", "Você já tem acesso a este curso.")

    customer_id = await _ensure_customer(db, aluno)
    kwargs = dict(
        mode="payment",
        customer=customer_id,
        line_items=[{"price": curso.stripe_price_id, "quantity": 1}],
        metadata={"app_user_id": str(aluno.id), "curso_slug": curso.slug},
        # Cliente digita o cupom na tela hospedada (admin cria em /admin/cupons).
        allow_promotion_codes=True,
        success_url=settings.stripe_success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=settings.stripe_cancel_url,
    )
    try:
        session = await run_in_threadpool(
            stripe.checkout.Session.create,
            payment_method_types=["card", "pix"],
            **kwargs,
        )
    except stripe.error.InvalidRequestError as exc:
        # Pix no BR pode estar em preview/por convite: sem ele na conta, a sessão
        # card+pix é recusada inteira. Degrada para só cartão em vez de perder a venda.
        if "pix" not in str(getattr(exc, "user_message", "") or exc).lower():
            raise _tratar_erro_stripe(exc)
        logger.warning(
            "Pix indisponível na conta Stripe — checkout avulso degradado para cartão."
        )
        try:
            session = await run_in_threadpool(
                stripe.checkout.Session.create,
                payment_method_types=["card"],
                **kwargs,
            )
        except stripe.error.StripeError as exc2:
            raise _tratar_erro_stripe(exc2)
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
@limiter.limit("10/minute")
async def checkout_assinatura_cartao(
    request: Request,
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
            allow_promotion_codes=True,
            metadata={"app_user_id": str(aluno.id), "plano_id": str(plano.id)},
            subscription_data={"metadata": {"app_user_id": str(aluno.id)}},
            success_url=settings.stripe_success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe_cancel_url,
        )
    except stripe.error.StripeError as exc:
        raise _tratar_erro_stripe(exc)

    return CheckoutCriado(checkout_url=session.url, session_id=session.id)


@router.post("/assinatura-pix", response_model=CheckoutCriado)
@limiter.limit("10/minute")
async def checkout_assinatura_pix(
    request: Request,
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
            allow_promotion_codes=True,
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
            success_url=settings.stripe_success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe_cancel_url,
        )
    except stripe.error.StripeError as exc:
        raise _tratar_erro_stripe(exc)

    return CheckoutCriado(checkout_url=session.url, session_id=session.id)


@router.get("/session/{session_id}", response_model=StatusCompra)
@limiter.limit("30/minute")
async def status_sessao(
    request: Request,
    # Valida o formato antes de qualquer IO: rejeita lixo sem gastar round-trip
    # ao Stripe (ids de sessão são `cs_test_`/`cs_live_` + alfanumérico).
    session_id: str = Path(..., pattern=r"^cs_(test|live)_[A-Za-z0-9]{10,100}$"),
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Status REAL da compra para a tela /sucesso (report-only).

    O acesso continua sendo concedido SÓ pelo webhook — aqui apenas conferimos o
    `payment_status` no Stripe e se a matrícula já foi criada, para a UI não
    afirmar 'pago' antes da confirmação. Só o dono da sessão pode consultar.
    """
    _exige_stripe()
    try:
        session = await run_in_threadpool(
            stripe.checkout.Session.retrieve, session_id
        )
    except stripe.error.InvalidRequestError:
        raise _err(404, "SESSAO_NAO_ENCONTRADA", "Sessão de checkout não encontrada.")
    except stripe.error.StripeError:
        logger.exception("Erro ao consultar a sessão de checkout")
        raise _err(502, "STRIPE_ERRO", "Não foi possível consultar o pagamento.")

    meta = dict(session.get("metadata") or {})
    # Não vaza status de sessão de terceiros (responde 404 como se não existisse).
    if meta.get("app_user_id") != str(aluno.id):
        raise _err(404, "SESSAO_NAO_ENCONTRADA", "Sessão de checkout não encontrada.")

    # Saída tipada: só repassa valores conhecidos do Stripe (allowlist).
    payment_status = session.get("payment_status") or "unpaid"
    if payment_status not in {"paid", "unpaid", "no_payment_required"}:
        payment_status = "unpaid"
    curso_slug = meta.get("curso_slug")

    # Acesso = matrícula ATIVA já criada pelo webhook. Avulso confere o curso da
    # sessão; assinatura (plano_id) libera o catálogo → qualquer matrícula ativa.
    if curso_slug:
        q = (
            select(Matricula.id)
            .join(Curso, Curso.id == Matricula.curso_id)
            .where(
                Matricula.aluno_id == aluno.id,
                Curso.slug == curso_slug,
                Matricula.status == StatusMatricula.ativo,
            )
        )
    else:
        q = select(Matricula.id).where(
            Matricula.aluno_id == aluno.id,
            Matricula.status == StatusMatricula.ativo,
        )
    acesso = (await db.scalar(q)) is not None

    if acesso:
        estado = "liberado"
    elif payment_status == "paid":
        estado = "processando"
    else:
        estado = "pendente"

    return StatusCompra(
        estado=estado,
        payment_status=payment_status,
        acesso_liberado=acesso,
        curso_slug=curso_slug,
    )
