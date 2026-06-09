"""Webhook de pagamento — multi-gateway (Stripe na Fase A).

Espelha o padrão de `webhooks_wa.py`: rota `@limiter.exempt` (servidor a servidor),
corpo CRU lido antes de qualquer parse, assinatura validada sobre os bytes crus.

Idempotência em DUAS camadas, tudo numa única transação:
- `WebhookEvento.event_id` único → deduplica reentrega do MESMO evento.
- `Pagamento.gateway_transaction_id` único (= id do PaymentIntent) → deduplica
  eventos DIFERENTES sobre o mesmo pagamento (ex.: cartão `completed` e Pix
  `async_payment_succeeded` convergem num só Pagamento, sem dupla concessão).
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import limiter
from app.models import (
    Aluno,
    Curso,
    Matricula,
    Pagamento,
    StatusMatricula,
    StatusPagamento,
    WebhookEvento,
)
from app.schemas.pagamentos import WebhookRecebido

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/pagamento", tags=["webhooks"])

_GATEWAYS_CONHECIDOS = {"stripe", "mercadopago", "asaas"}

# Eventos do Stripe (mode=payment) que liberam acesso ou registram falha.
_EVENTOS_CONCESSAO = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
}
_EVENTOS_FALHA = {
    "checkout.session.async_payment_failed",
    "payment_intent.payment_failed",
}


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


# ── Endpoint ────────────────────────────────────────────────────────────────────

@router.post("/{gateway}", response_model=WebhookRecebido)
@limiter.exempt
async def webhook_pagamento(
    request: Request,
    gateway: str,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
):
    if gateway not in _GATEWAYS_CONHECIDOS:
        raise _err(404, "GATEWAY_DESCONHECIDO", f"Gateway '{gateway}' não suportado.")
    if gateway != "stripe":
        raise _err(
            501, "GATEWAY_NAO_IMPLEMENTADO", f"Gateway '{gateway}' ainda não implementado."
        )

    body_bytes = await request.body()
    event = _verificar_stripe(body_bytes, stripe_signature)
    await _processar_stripe(db, event)
    return WebhookRecebido(received=True)


# ── Validação de assinatura ─────────────────────────────────────────────────────

def _verificar_stripe(body_bytes: bytes, sig_header: str | None) -> dict[str, Any]:
    """Valida a assinatura e devolve o evento como dict puro.

    Fail-CLOSED: webhook de pagamento NUNCA processa payload não verificado. Sem
    `STRIPE_WEBHOOK_SECRET` o endpoint recusa (503) em vez de aceitar sem assinatura.
    """
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        logger.error("STRIPE_WEBHOOK_SECRET ausente — webhook recusado (fail-closed).")
        raise _err(
            503, "WEBHOOK_NAO_CONFIGURADO",
            "Webhook de pagamento não configurado (sem segredo de assinatura).",
        )
    if not sig_header:
        raise _err(401, "ASSINATURA_AUSENTE", "Header Stripe-Signature obrigatório.")
    try:
        stripe.Webhook.construct_event(body_bytes, sig_header, secret)
    except ValueError:
        raise _err(400, "PAYLOAD_INVALIDO", "Corpo da requisição não é JSON válido.")
    except stripe.error.SignatureVerificationError:
        raise _err(401, "ASSINATURA_INVALIDA", "Assinatura Stripe inválida.")

    try:
        return json.loads(body_bytes)
    except json.JSONDecodeError:
        raise _err(400, "PAYLOAD_INVALIDO", "Corpo da requisição não é JSON válido.")


# ── Núcleo de processamento (uma transação) ─────────────────────────────────────

async def _processar_stripe(db: AsyncSession, event: dict[str, Any]) -> None:
    tipo = event.get("type", "")
    event_id = event.get("id", "")
    obj: dict[str, Any] = (event.get("data") or {}).get("object") or {}

    # 1) Idempotência por event.id — grava (flush, sem commit). Reentrega → no-op.
    if event_id:
        db.add(WebhookEvento(event_id=event_id, gateway="stripe", tipo=tipo))
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            logger.info("Evento Stripe duplicado ignorado: %s", event_id)
            return

    if tipo in _EVENTOS_CONCESSAO:
        await _conceder_acesso(db, event, obj, tipo)
    elif tipo in _EVENTOS_FALHA:
        await _registrar_falha(db, event, obj)
    else:
        logger.debug("Evento Stripe sem ação: %s", tipo)

    await db.commit()


async def _conceder_acesso(
    db: AsyncSession, event: dict[str, Any], session_obj: dict[str, Any], tipo: str
) -> None:
    # Cartão confirma já no completed (payment_status == "paid"). Pix chega como
    # completed NÃO pago e confirma depois em async_payment_succeeded.
    if tipo == "checkout.session.completed" and session_obj.get("payment_status") != "paid":
        logger.info("checkout.session.completed ainda não pago (Pix pendente) — sem concessão.")
        return

    pi_id = session_obj.get("payment_intent")
    if not pi_id:
        logger.warning("Sessão sem payment_intent — sem concessão (event=%s).", event.get("id"))
        return

    metadata = session_obj.get("metadata") or {}
    aluno = await _resolver_aluno(db, metadata.get("app_user_id"), session_obj.get("customer"))
    curso = await _resolver_curso(db, metadata.get("curso_slug"))
    valor = _valor_em_reais(session_obj.get("amount_total"))

    # Dedup por pagamento (PI id). Se já aprovado, não concede de novo.
    pag = (
        await db.execute(select(Pagamento).where(Pagamento.gateway_transaction_id == pi_id))
    ).scalar_one_or_none()
    ja_aprovado = pag is not None and pag.status == StatusPagamento.aprovado

    customer = session_obj.get("customer")
    if aluno is not None and customer and not aluno.stripe_customer_id:
        aluno.stripe_customer_id = customer

    if pag is None:
        pag = Pagamento(
            aluno_id=(aluno.id if aluno else None),
            gateway="stripe",
            gateway_transaction_id=pi_id,
            valor=valor,
            status=StatusPagamento.aprovado,
            payload=event,
        )
        db.add(pag)
    else:
        pag.status = StatusPagamento.aprovado
        if aluno is not None and pag.aluno_id is None:
            pag.aluno_id = aluno.id
    await db.flush()

    if aluno is None or curso is None:
        # Pagamento gravado para reconciliação manual (aluno_id é nullable).
        logger.warning(
            "Pagamento %s sem aluno/curso (app_user_id=%s, curso_slug=%s) — "
            "gravado para reconciliação.",
            pi_id, metadata.get("app_user_id"), metadata.get("curso_slug"),
        )
        return

    if ja_aprovado:
        logger.info("Pagamento %s já aprovado — matrícula não duplicada.", pi_id)
        return

    await _criar_ou_renovar_matricula(db, aluno.id, curso, pag.id)


async def _registrar_falha(
    db: AsyncSession, event: dict[str, Any], obj: dict[str, Any]
) -> None:
    """Pagamento recusado: grava/atualiza sem mexer na matrícula. Não rebaixa aprovado."""
    pi_id = obj.get("payment_intent") or obj.get("id")
    if not pi_id:
        return
    pag = (
        await db.execute(select(Pagamento).where(Pagamento.gateway_transaction_id == pi_id))
    ).scalar_one_or_none()
    if pag is None:
        metadata = obj.get("metadata") or {}
        aluno = await _resolver_aluno(db, metadata.get("app_user_id"), obj.get("customer"))
        db.add(Pagamento(
            aluno_id=(aluno.id if aluno else None),
            gateway="stripe",
            gateway_transaction_id=pi_id,
            valor=_valor_em_reais(obj.get("amount_total") or obj.get("amount")),
            status=StatusPagamento.recusado,
            payload=event,
        ))
    elif pag.status != StatusPagamento.aprovado:
        pag.status = StatusPagamento.recusado


# ── Helpers ──────────────────────────────────────────────────────────────────────

async def _resolver_aluno(
    db: AsyncSession, app_user_id: str | None, customer: str | None
) -> Aluno | None:
    if app_user_id:
        try:
            aid = uuid.UUID(app_user_id)
        except (ValueError, TypeError, AttributeError):
            aid = None
        if aid is not None:
            aluno = (
                await db.execute(select(Aluno).where(Aluno.id == aid))
            ).scalar_one_or_none()
            if aluno is not None:
                return aluno
    if customer:
        return (
            await db.execute(select(Aluno).where(Aluno.stripe_customer_id == customer))
        ).scalar_one_or_none()
    return None


async def _resolver_curso(db: AsyncSession, slug: str | None) -> Curso | None:
    if not slug:
        return None
    return (
        await db.execute(select(Curso).where(Curso.slug == slug))
    ).scalar_one_or_none()


def _valor_em_reais(amount: int | None) -> Decimal:
    """Stripe envia o valor em centavos (int) → converte para Decimal em reais."""
    if amount is None:
        return Decimal("0.00")
    return (Decimal(int(amount)) / 100).quantize(Decimal("0.01"))


async def _criar_ou_renovar_matricula(
    db: AsyncSession, aluno_id: uuid.UUID, curso: Curso, pagamento_id: uuid.UUID
) -> None:
    """Contrato §7: data_expiracao = agora + curso.validade_dias (sempre a partir de agora)."""
    agora = datetime.now(timezone.utc)
    nova_exp = agora + timedelta(days=curso.validade_dias)
    mat = (
        await db.execute(
            select(Matricula).where(
                Matricula.aluno_id == aluno_id, Matricula.curso_id == curso.id
            )
        )
    ).scalar_one_or_none()
    if mat is None:
        db.add(Matricula(
            aluno_id=aluno_id,
            curso_id=curso.id,
            pagamento_id=pagamento_id,
            status=StatusMatricula.ativo,
            data_expiracao=nova_exp,
        ))
    else:
        mat.status = StatusMatricula.ativo
        mat.data_expiracao = nova_exp
        mat.pagamento_id = pagamento_id
