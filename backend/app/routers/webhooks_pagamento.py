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

# Teto do corpo do webhook (eventos do Stripe são pequenos). A rota é isenta de
# rate limit (servidor a servidor), então um corpo gigante é rejeitado antes do
# parse/verificação para não consumir memória/CPU à toa.
_MAX_BODY_BYTES = 256 * 1024

# Eventos do Stripe (mode=payment) que liberam acesso ou registram falha.
_EVENTOS_CONCESSAO = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
}
_EVENTOS_FALHA = {
    "checkout.session.async_payment_failed",
    "payment_intent.payment_failed",
    "invoice.payment_failed",
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
    if len(body_bytes) > _MAX_BODY_BYTES:
        raise _err(413, "PAYLOAD_GRANDE_DEMAIS", "Corpo do webhook excede o limite.")
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

    # Evento sem id não pode ser deduplicado pela 1ª camada — recusa (defesa em
    # profundidade; eventos reais do Stripe sempre têm id).
    if not event_id:
        raise _err(400, "EVENTO_SEM_ID", "Evento Stripe sem id — recusado.")

    # Em produção, recusa eventos de test-mode: mesmo assinados, um evento disparado
    # via Stripe CLI/test-mode (livemode=false) não pode conceder acesso real. 200
    # para o Stripe não reentregar (no-op consciente).
    if settings.is_production and event.get("livemode") is not True:
        logger.warning("Evento Stripe test-mode (livemode!=true) ignorado em produção: %s", event_id)
        return

    # 1) Idempotência por event.id — grava (flush, sem commit). Reentrega → no-op.
    db.add(WebhookEvento(event_id=event_id, gateway="stripe", tipo=tipo))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("Evento Stripe duplicado ignorado: %s", event_id)
        return

    # Corrida: dois eventos DIFERENTES sobre o mesmo pagamento (ex.: cartão
    # `completed` e Pix `async_payment_succeeded`) podem inserir Pagamento com o
    # mesmo gateway_transaction_id concorrentemente. O unique constraint garante
    # que não há dupla concessão; aqui tratamos o IntegrityError como no-op (o
    # evento concorrente já concedeu) em vez de devolver 500.
    try:
        if tipo in _EVENTOS_CONCESSAO:
            await _conceder_acesso(db, event, obj, tipo)
        elif tipo == "invoice.paid":
            await _conceder_assinatura(db, event, obj)
        elif tipo == "customer.subscription.deleted":
            await _revogar_assinatura(db, obj)
        elif tipo in _EVENTOS_FALHA:
            await _registrar_falha(db, event, obj)
        else:
            logger.debug("Evento Stripe sem ação: %s", tipo)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.info(
            "IntegrityError no processamento (corrida do mesmo pagamento) — no-op: %s",
            event_id,
        )


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
            payload=_payload_reconciliacao(event),
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
            valor=_valor_em_reais(
                obj.get("amount_total") or obj.get("amount") or obj.get("amount_due")
            ),
            status=StatusPagamento.recusado,
            payload=_payload_reconciliacao(event),
        ))
    elif pag.status != StatusPagamento.aprovado:
        pag.status = StatusPagamento.recusado


# ── Assinaturas (mode=subscription) ─────────────────────────────────────────────

def _sub_details(invoice: dict[str, Any]) -> dict[str, Any]:
    """Detalhes da assinatura no invoice — compat com os DOIS formatos da API.

    Legado (<2025): `invoice.subscription` (id) e `invoice.subscription_details`.
    Atual (basil/dahlia): tudo em `invoice.parent.subscription_details`
    (`{"subscription": "sub_...", "metadata": {...}}`).
    """
    parent = invoice.get("parent") or {}
    return (
        invoice.get("subscription_details")
        or parent.get("subscription_details")
        or {}
    )


def _sub_id_do_invoice(invoice: dict[str, Any]) -> str | None:
    return invoice.get("subscription") or _sub_details(invoice).get("subscription")


async def _conceder_assinatura(
    db: AsyncSession, event: dict[str, Any], invoice: dict[str, Any]
) -> None:
    """invoice.paid → libera/renova acesso ao catálogo inteiro até o fim do ciclo."""
    sub_id = _sub_id_do_invoice(invoice)
    invoice_id = invoice.get("id")
    if not sub_id or not invoice_id:
        logger.warning("invoice.paid sem subscription/id — ignorado (event=%s).", event.get("id"))
        return

    pag = (
        await db.execute(select(Pagamento).where(Pagamento.gateway_transaction_id == invoice_id))
    ).scalar_one_or_none()
    ja_aprovado = pag is not None and pag.status == StatusPagamento.aprovado

    aluno = await _resolver_aluno_assinatura(db, invoice)
    valor = _valor_em_reais(invoice.get("amount_paid") or invoice.get("amount_due"))

    if pag is None:
        pag = Pagamento(
            aluno_id=(aluno.id if aluno else None),
            gateway="stripe",
            gateway_transaction_id=invoice_id,
            valor=valor,
            status=StatusPagamento.aprovado,
            payload=_payload_reconciliacao(event),
        )
        db.add(pag)
    else:
        pag.status = StatusPagamento.aprovado
        if aluno is not None and pag.aluno_id is None:
            pag.aluno_id = aluno.id
    await db.flush()

    if aluno is None:
        logger.warning(
            "invoice.paid %s sem aluno (customer=%s) — gravado p/ reconciliação.",
            invoice_id, invoice.get("customer"),
        )
        return
    if ja_aprovado:
        logger.info("Invoice %s já processada — assinatura não reprocessada.", invoice_id)
        return

    await _liberar_catalogo(db, aluno.id, sub_id, pag.id, _fim_periodo(invoice))


async def _revogar_assinatura(db: AsyncSession, sub: dict[str, Any]) -> None:
    """customer.subscription.deleted → expira as matrículas concedidas pela assinatura."""
    sub_id = sub.get("id")
    if not sub_id:
        return
    mats = (
        await db.execute(
            select(Matricula).where(Matricula.stripe_subscription_id == sub_id)
        )
    ).scalars().all()
    for m in mats:
        m.status = StatusMatricula.expirado


async def _resolver_aluno_assinatura(
    db: AsyncSession, invoice: dict[str, Any]
) -> Aluno | None:
    meta = _sub_details(invoice).get("metadata") or {}
    return await _resolver_aluno(db, meta.get("app_user_id"), invoice.get("customer"))


def _fim_periodo(invoice: dict[str, Any]) -> datetime:
    """Fim do ciclo pago = period.end da linha da assinatura (sem chamada extra à API)."""
    for linha in (invoice.get("lines") or {}).get("data") or []:
        fim = (linha.get("period") or {}).get("end")
        if fim:
            return datetime.fromtimestamp(int(fim), tz=timezone.utc)
    fim = invoice.get("period_end")
    if fim:
        return datetime.fromtimestamp(int(fim), tz=timezone.utc)
    return datetime.now(timezone.utc) + timedelta(days=30)


async def _liberar_catalogo(
    db: AsyncSession,
    aluno_id: uuid.UUID,
    sub_id: str,
    pagamento_id: uuid.UUID,
    period_end: datetime,
) -> None:
    """Acesso total: cria/renova matrícula ativa em TODOS os cursos até period_end."""
    curso_ids = (await db.execute(select(Curso.id))).scalars().all()
    existentes = {
        m.curso_id: m
        for m in (
            await db.execute(select(Matricula).where(Matricula.aluno_id == aluno_id))
        ).scalars().all()
    }
    for curso_id in curso_ids:
        mat = existentes.get(curso_id)
        if mat is None:
            db.add(Matricula(
                aluno_id=aluno_id,
                curso_id=curso_id,
                pagamento_id=pagamento_id,
                stripe_subscription_id=sub_id,
                status=StatusMatricula.ativo,
                data_expiracao=period_end,
            ))
        else:
            mat.status = StatusMatricula.ativo
            mat.data_expiracao = period_end
            mat.stripe_subscription_id = sub_id
            mat.pagamento_id = pagamento_id


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


def _payload_reconciliacao(event: dict[str, Any]) -> dict[str, Any]:
    """Guarda só o necessário para reconciliação, SEM PII do cliente (LGPD).

    O evento Stripe cru traz `customer_details`/`customer_email`/`billing_details`
    (nome, e-mail). Aqui mantemos apenas ids, valores e a metadata (que é nossa).
    """
    obj = (event.get("data") or {}).get("object") or {}
    campos = (
        "id", "object", "mode", "status", "payment_status",
        "payment_intent", "subscription", "invoice",
        "amount_total", "amount_paid", "amount_due", "currency",
        "customer", "metadata",
    )
    return {
        "id": event.get("id"),
        "type": event.get("type"),
        "created": event.get("created"),
        "livemode": event.get("livemode"),
        "object": {k: obj.get(k) for k in campos if obj.get(k) is not None},
    }


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
