"""Testes do webhook de status do WhatsApp (POST /api/v1/webhooks/whatsapp/status).

Espelha tests/test_webhooks_pagamento.py: assina de verdade (HMAC-SHA256 do corpo
cru, header X-Hub-Signature-256) para exercitar o caminho real de validação — sem
mockar o verificador. Cobre fail-CLOSED por provedor: Meta valida assinatura;
Twilio/Z-API são recusados (501); provedor ausente/sem segredo recusa (503).
"""
import hashlib
import hmac
import json
import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Aluno,
    CanalNotificacao,
    Notificacao,
    StatusNotificacao,
    TipoNotificacao,
)

URL = "/api/v1/webhooks/whatsapp/status"
SECRET = "wa_test_app_secret"


def _assinar(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _meta_payload(msg_id: str, status: str = "delivered") -> dict:
    """Payload bruto da Meta Cloud API com um único status."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"statuses": [{"id": msg_id, "status": status}]}}]}],
    }


async def _post(
    client: AsyncClient,
    payload: dict | bytes,
    *,
    secret: str = SECRET,
    sign: bool = True,
    sig: str | None = None,
):
    body = json.dumps(payload).encode() if isinstance(payload, dict) else payload
    headers = {"Content-Type": "application/json"}
    if sig is not None:
        headers["X-Hub-Signature-256"] = sig
    elif sign:
        headers["X-Hub-Signature-256"] = _assinar(body, secret)
    return await client.post(URL, content=body, headers=headers)


@pytest_asyncio.fixture
async def seed_notif():
    """Aluno + Notificacao(WhatsApp, pendente) com provedor_msg_id conhecido."""
    pref = uuid.uuid4().hex[:8]
    msg_id = f"wamid.{pref}"
    async with AsyncSessionLocal() as db:
        aluno = Aluno(
            nome="WA Tester",
            email=f"wa_{pref}@rodelcar.dev",
            senha_hash=hash_password("x"),
        )
        db.add(aluno)
        await db.flush()
        notif = Notificacao(
            aluno_id=aluno.id,
            matricula_id=None,
            canal=CanalNotificacao.whatsapp,
            tipo=TipoNotificacao.vigencia_proxima,
            marco="7d",
            status=StatusNotificacao.pendente,
            provedor_msg_id=msg_id,
        )
        db.add(notif)
        await db.commit()
        data = {"aluno_id": str(aluno.id), "msg_id": msg_id, "notif_id": str(notif.id)}

    yield data

    aid = uuid.UUID(data["aluno_id"])
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Notificacao).where(Notificacao.aluno_id == aid))
        await db.execute(delete(Aluno).where(Aluno.id == aid))
        await db.commit()


async def _notif(notif_id: str) -> Notificacao:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(
                select(Notificacao).where(Notificacao.id == uuid.UUID(notif_id))
            )
        ).scalar_one()


class TestWebhookWhatsAppMeta:
    async def test_assinatura_valida_atualiza_status(
        self, client: AsyncClient, seed_notif, monkeypatch
    ):
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_APP_SECRET", SECRET)
        resp = await _post(client, _meta_payload(seed_notif["msg_id"], "delivered"))
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

        notif = await _notif(seed_notif["notif_id"])
        assert notif.status == StatusNotificacao.enviada
        assert notif.enviada_em is not None

    async def test_formato_normalizado_failed(
        self, client: AsyncClient, seed_notif, monkeypatch
    ):
        # Formato normalizado interno ({provedor_msg_id, status}) também exige assinatura.
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_APP_SECRET", SECRET)
        resp = await _post(
            client, {"provedor_msg_id": seed_notif["msg_id"], "status": "failed"}
        )
        assert resp.status_code == 200

        notif = await _notif(seed_notif["notif_id"])
        assert notif.status == StatusNotificacao.falhou

    async def test_assinatura_invalida_401(
        self, client: AsyncClient, seed_notif, monkeypatch
    ):
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_APP_SECRET", SECRET)
        resp = await _post(client, _meta_payload(seed_notif["msg_id"]), sig="sha256=deadbeef")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "ASSINATURA_INVALIDA"

        notif = await _notif(seed_notif["notif_id"])
        assert notif.status == StatusNotificacao.pendente  # não tocou

    async def test_assinatura_de_outro_segredo_401(
        self, client: AsyncClient, seed_notif, monkeypatch
    ):
        # Assinada com segredo errado: o HMAC bate em tamanho mas não em valor.
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_APP_SECRET", SECRET)
        resp = await _post(
            client, _meta_payload(seed_notif["msg_id"]), secret="segredo_errado"
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "ASSINATURA_INVALIDA"

    async def test_assinatura_ausente_401(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_APP_SECRET", SECRET)
        resp = await _post(client, _meta_payload("wamid.x"), sign=False)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "ASSINATURA_AUSENTE"

    async def test_sem_segredo_configurado_503(self, client: AsyncClient, monkeypatch):
        # fail-closed: provider=meta sem WA_META_APP_SECRET → recusa sem processar.
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_APP_SECRET", "")
        resp = await client.post(URL, content=b'{"object":"whatsapp_business_account"}')
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "WEBHOOK_NAO_CONFIGURADO"

    async def test_payload_invalido_400(self, client: AsyncClient, monkeypatch):
        # Assinatura válida sobre corpo que não é JSON → 400 após verificar.
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_APP_SECRET", SECRET)
        resp = await _post(client, b"isto-nao-e-json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "PAYLOAD_INVALIDO"


class TestWebhookWhatsAppProvider:
    async def test_provider_vazio_503(self, client: AsyncClient, monkeypatch):
        # fail-closed: sem WA_PROVIDER nenhum payload é aceito.
        monkeypatch.setattr(settings, "WA_PROVIDER", "")
        resp = await client.post(URL, content=b'{"object":"whatsapp_business_account"}')
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "WEBHOOK_NAO_CONFIGURADO"

    async def test_provider_twilio_501(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(settings, "WA_PROVIDER", "twilio")
        resp = await client.post(URL, content=b"{}")
        assert resp.status_code == 501
        assert resp.json()["error"]["code"] == "PROVEDOR_NAO_IMPLEMENTADO"

    async def test_provider_zapi_501(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(settings, "WA_PROVIDER", "zapi")
        resp = await client.post(URL, content=b"{}")
        assert resp.status_code == 501
        assert resp.json()["error"]["code"] == "PROVEDOR_NAO_IMPLEMENTADO"


class TestHandshakeGet:
    async def test_handshake_valido_devolve_challenge(
        self, client: AsyncClient, monkeypatch
    ):
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_VERIFY_TOKEN", "vt_test")
        resp = await client.get(
            URL,
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "vt_test",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "12345"

    async def test_handshake_token_invalido_403(self, client: AsyncClient, monkeypatch):
        monkeypatch.setattr(settings, "WA_PROVIDER", "meta")
        monkeypatch.setattr(settings, "WA_META_VERIFY_TOKEN", "vt_test")
        resp = await client.get(
            URL,
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "ERRADO",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    async def test_handshake_provider_nao_meta_403(
        self, client: AsyncClient, monkeypatch
    ):
        # fail-closed: verify token setado, mas provider != meta → recusa.
        monkeypatch.setattr(settings, "WA_PROVIDER", "twilio")
        monkeypatch.setattr(settings, "WA_META_VERIFY_TOKEN", "vt_test")
        resp = await client.get(
            URL,
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "vt_test",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
