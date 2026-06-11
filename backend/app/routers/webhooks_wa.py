"""Webhook de status do WhatsApp — suporte a Meta Cloud API e formato normalizado."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import limiter
from app.models import Notificacao, StatusNotificacao

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])

# Teto do corpo (rota isenta de rate limit): rejeita payload gigante antes do parse.
_MAX_BODY_BYTES = 256 * 1024


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


# ── Handshake GET (Meta Cloud API) ────────────────────────────────────────────

@router.get("/status")
@limiter.exempt
async def wa_verify(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    # Handshake é exclusivo da Meta Cloud API. Fail-closed: sem provider=meta ou
    # sem WA_META_VERIFY_TOKEN configurado, recusa (não devolve o challenge).
    if (
        settings.WA_PROVIDER.strip().lower() == "meta"
        and hub_mode == "subscribe"
        and hub_verify_token
        and settings.WA_META_VERIFY_TOKEN
        and hmac.compare_digest(hub_verify_token, settings.WA_META_VERIFY_TOKEN)
        and hub_challenge
    ):
        return Response(content=hub_challenge, media_type="text/plain")
    raise _err(403, "FORBIDDEN", "Verify token inválido.")


# ── Payload normalizado (usado internamente e em testes) ──────────────────────

class _StatusNormalizado(BaseModel):
    provedor_msg_id: str
    status: str         # sent | delivered | read | failed
    erro: str | None = None


_STATUS_MAP = {
    "sent": StatusNotificacao.enviada,
    "delivered": StatusNotificacao.enviada,
    "read": StatusNotificacao.enviada,
    "failed": StatusNotificacao.falhou,
}


def _extrair_meta(payload: dict[str, Any]) -> list[_StatusNormalizado]:
    """Normaliza payload bruto da Meta Cloud API."""
    statuses: list[_StatusNormalizado] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for s in change.get("value", {}).get("statuses", []):
                erro = None
                if s.get("errors"):
                    erro = s["errors"][0].get("message")
                statuses.append(
                    _StatusNormalizado(
                        provedor_msg_id=s.get("id", ""),
                        status=s.get("status", ""),
                        erro=erro,
                    )
                )
    return statuses


async def _atualizar_notificacao(
    db: AsyncSession, s: _StatusNormalizado, agora: datetime
) -> None:
    if not s.provedor_msg_id:
        return
    result = await db.execute(
        select(Notificacao).where(Notificacao.provedor_msg_id == s.provedor_msg_id)
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        logger.debug("provedor_msg_id não encontrado: %s", s.provedor_msg_id)
        return

    novo_status = _STATUS_MAP.get(s.status.lower())
    if novo_status:
        notif.status = novo_status
        if novo_status == StatusNotificacao.enviada and not notif.enviada_em:
            notif.enviada_em = agora
    await db.commit()


# ── Validação de assinatura ─────────────────────────────────────────────────────

def _verificar_assinatura(body_bytes: bytes, x_hub_signature_256: str | None) -> None:
    """Valida a assinatura do webhook conforme o `WA_PROVIDER`.

    Fail-CLOSED, igual ao webhook Stripe (`webhooks_pagamento._verificar_stripe`):
    NUNCA processa payload não verificado. Só a Meta Cloud API tem validação
    implementada (HMAC-SHA256 sobre o corpo cru, header X-Hub-Signature-256).
    Twilio/Z-API usam esquemas próprios ainda não implementados → recusados.
    Provider ausente/desconhecido também é recusado.
    """
    provider = settings.WA_PROVIDER.strip().lower()

    if provider == "meta":
        secret = settings.WA_META_APP_SECRET
        if not secret:
            logger.error("WA_META_APP_SECRET ausente — webhook recusado (fail-closed).")
            raise _err(
                503, "WEBHOOK_NAO_CONFIGURADO",
                "Webhook de WhatsApp não configurado (sem segredo de assinatura).",
            )
        if not x_hub_signature_256:
            raise _err(401, "ASSINATURA_AUSENTE", "Header X-Hub-Signature-256 obrigatório.")
        computed = "sha256=" + hmac.new(
            secret.encode(), body_bytes, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(computed, x_hub_signature_256):
            raise _err(401, "ASSINATURA_INVALIDA", "Assinatura HMAC-SHA256 inválida.")
        return

    if provider in {"twilio", "zapi"}:
        logger.error(
            "WA_PROVIDER=%s sem validação de assinatura implementada — recusado.", provider
        )
        raise _err(
            501, "PROVEDOR_NAO_IMPLEMENTADO",
            f"Validação de webhook do provedor '{provider}' ainda não implementada.",
        )

    logger.error("WA_PROVIDER ausente/desconhecido (%r) — webhook recusado (fail-closed).", provider)
    raise _err(
        503, "WEBHOOK_NAO_CONFIGURADO",
        "Webhook de WhatsApp não configurado (defina WA_PROVIDER).",
    )


# ── POST de status ─────────────────────────────────────────────────────────────

@router.post("/status")
@limiter.exempt
async def wa_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str | None = Header(None),
):
    body_bytes = await request.body()
    if len(body_bytes) > _MAX_BODY_BYTES:
        raise _err(413, "PAYLOAD_GRANDE_DEMAIS", "Corpo do webhook excede o limite.")
    _verificar_assinatura(body_bytes, x_hub_signature_256)

    try:
        payload: dict[str, Any] = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise _err(400, "PAYLOAD_INVALIDO", "Corpo da requisição não é JSON válido.")

    # Auto-detecção de formato
    if "provedor_msg_id" in payload:
        statuses = [_StatusNormalizado(**payload)]
    elif payload.get("object") == "whatsapp_business_account":
        statuses = _extrair_meta(payload)
    else:
        logger.warning("Formato de webhook WhatsApp não reconhecido — ignorado")
        return {"received": True}

    agora = datetime.now(timezone.utc)
    for s in statuses:
        await _atualizar_notificacao(db, s, agora)

    return {"received": True}
