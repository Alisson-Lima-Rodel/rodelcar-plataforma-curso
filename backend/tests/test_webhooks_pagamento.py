"""Testes do webhook de pagamento Stripe (POST /api/v1/webhooks/pagamento/stripe).

Assina de verdade (header `t=...,v1=hmac_sha256(secret, "{ts}.{body}")`) com timestamp
atual, para exercitar o caminho real de `stripe.Webhook.construct_event` — sem mockar o
verificador. Seed direto de Aluno+Curso, cleanup em ordem de FK.
"""
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Aluno,
    Curso,
    Matricula,
    Pagamento,
    StatusMatricula,
    StatusPagamento,
    TipoCurso,
    WebhookEvento,
)

URL = "/api/v1/webhooks/pagamento/stripe"
SECRET = "whsec_test_rodelcar"


def _assinar(body: str, secret: str = SECRET) -> str:
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _session_event(
    tipo: str,
    *,
    event_id: str,
    pi_id: str,
    aluno_id: str,
    curso_slug: str,
    payment_status: str = "paid",
    amount_total: int = 49700,
    customer: str = "cus_test",
) -> dict:
    return {
        "id": event_id,
        "type": tipo,
        "data": {
            "object": {
                "id": f"cs_{pi_id}",
                "object": "checkout.session",
                "payment_status": payment_status,
                "payment_intent": pi_id,
                "amount_total": amount_total,
                "customer": customer,
                "metadata": {"app_user_id": aluno_id, "curso_slug": curso_slug},
            }
        },
    }


async def _post(client: AsyncClient, event: dict, *, assinar: bool = True, sig: str | None = None):
    body = json.dumps(event)
    headers = {"Content-Type": "application/json"}
    if sig is not None:
        headers["Stripe-Signature"] = sig
    elif assinar:
        headers["Stripe-Signature"] = _assinar(body)
    return await client.post(URL, content=body, headers=headers)


@pytest_asyncio.fixture
async def seed():
    """Aluno + Curso avulso únicos; limpa Matrícula/Pagamento/WebhookEvento ao fim."""
    pref = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        aluno = Aluno(
            nome="Stripe Tester",
            email=f"stripe_{pref}@rodelcar.dev",
            senha_hash=hash_password("x"),
        )
        db.add(aluno)
        await db.flush()
        curso = Curso(
            slug=f"stripe-{pref}",
            titulo="Curso Stripe Teste",
            tipo=TipoCurso.avulso,
            preco=Decimal("497.00"),
            validade_dias=365,
            stripe_price_id=f"price_{pref}",
        )
        db.add(curso)
        await db.flush()
        await db.commit()
        data = {
            "pref": pref,
            "aluno_id": str(aluno.id),
            "curso_id": str(curso.id),
            "curso_slug": curso.slug,
            "validade_dias": curso.validade_dias,
        }

    yield data

    aid = uuid.UUID(data["aluno_id"])
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Matricula).where(Matricula.aluno_id == aid))
        await db.execute(delete(Pagamento).where(Pagamento.aluno_id == aid))
        await db.execute(
            delete(Pagamento).where(Pagamento.gateway_transaction_id.like(f"%{pref}%"))
        )
        await db.execute(delete(WebhookEvento).where(WebhookEvento.event_id.like(f"%{pref}%")))
        await db.execute(delete(Curso).where(Curso.id == uuid.UUID(data["curso_id"])))
        await db.execute(delete(Aluno).where(Aluno.id == aid))
        await db.commit()


async def _pagamentos(aluno_id: str) -> list[Pagamento]:
    async with AsyncSessionLocal() as db:
        return list(
            (
                await db.execute(
                    select(Pagamento).where(Pagamento.aluno_id == uuid.UUID(aluno_id))
                )
            ).scalars().all()
        )


async def _matriculas(aluno_id: str) -> list[Matricula]:
    async with AsyncSessionLocal() as db:
        return list(
            (
                await db.execute(
                    select(Matricula).where(Matricula.aluno_id == uuid.UUID(aluno_id))
                )
            ).scalars().all()
        )


class TestWebhookStripe:
    async def test_cartao_aprovado_cria_matricula(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        event = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_1",
            pi_id=f"pi_{pref}_1",
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        resp = await _post(client, event)
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

        pagamentos = await _pagamentos(seed["aluno_id"])
        assert len(pagamentos) == 1
        assert pagamentos[0].status == StatusPagamento.aprovado
        assert pagamentos[0].valor == Decimal("497.00")
        assert pagamentos[0].gateway_transaction_id == f"pi_{pref}_1"

        matriculas = await _matriculas(seed["aluno_id"])
        assert len(matriculas) == 1
        assert matriculas[0].status == StatusMatricula.ativo
        esperado = datetime.now(timezone.utc) + timedelta(days=seed["validade_dias"])
        assert abs((matriculas[0].data_expiracao - esperado).total_seconds()) < 120

    async def test_evento_duplicado_nao_duplica(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        event = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_dup",
            pi_id=f"pi_{pref}_dup",
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        r1 = await _post(client, event)
        r2 = await _post(client, event)  # mesmo event.id → no-op
        assert r1.status_code == 200 and r2.status_code == 200
        assert len(await _pagamentos(seed["aluno_id"])) == 1
        assert len(await _matriculas(seed["aluno_id"])) == 1

    async def test_mesmo_pi_eventos_diferentes_nao_duplica(
        self, client: AsyncClient, seed, monkeypatch
    ):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        pi = f"pi_{pref}_pi"
        ev1 = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_a",
            pi_id=pi,
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        ev2 = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_b",  # evento diferente, MESMO PaymentIntent
            pi_id=pi,
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        assert (await _post(client, ev1)).status_code == 200
        assert (await _post(client, ev2)).status_code == 200
        assert len(await _pagamentos(seed["aluno_id"])) == 1
        assert len(await _matriculas(seed["aluno_id"])) == 1

    async def test_pix_pendente_depois_confirma(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        pi = f"pi_{pref}_pix"
        # 1) completed ainda NÃO pago (Pix pendente) → sem concessão
        pendente = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_pixpend",
            pi_id=pi,
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
            payment_status="unpaid",
        )
        assert (await _post(client, pendente)).status_code == 200
        assert len(await _matriculas(seed["aluno_id"])) == 0
        assert len(await _pagamentos(seed["aluno_id"])) == 0

        # 2) async_payment_succeeded → concede
        ok = _session_event(
            "checkout.session.async_payment_succeeded",
            event_id=f"evt_{pref}_pixok",
            pi_id=pi,
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        assert (await _post(client, ok)).status_code == 200
        mats = await _matriculas(seed["aluno_id"])
        assert len(mats) == 1 and mats[0].status == StatusMatricula.ativo
        assert len(await _pagamentos(seed["aluno_id"])) == 1

    async def test_assinatura_invalida_401(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        event = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{seed['pref']}_bad",
            pi_id=f"pi_{seed['pref']}_bad",
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        resp = await _post(client, event, sig="t=123,v1=deadbeef")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "ASSINATURA_INVALIDA"
        assert len(await _matriculas(seed["aluno_id"])) == 0

    async def test_assinatura_ausente_401(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        event = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{seed['pref']}_nosig",
            pi_id=f"pi_{seed['pref']}_nosig",
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        resp = await _post(client, event, assinar=False)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "ASSINATURA_AUSENTE"

    async def test_sem_segredo_configurado_503(self, client: AsyncClient, monkeypatch):
        # fail-closed: sem STRIPE_WEBHOOK_SECRET, recusa sem processar.
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        resp = await client.post(URL, content=b'{"id":"evt_x","type":"x"}')
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "WEBHOOK_NAO_CONFIGURADO"

    async def test_renovacao_atualiza_expiracao(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        # matrícula pré-existente vencida
        async with AsyncSessionLocal() as db:
            db.add(Matricula(
                aluno_id=uuid.UUID(seed["aluno_id"]),
                curso_id=uuid.UUID(seed["curso_id"]),
                status=StatusMatricula.expirado,
                data_expiracao=datetime.now(timezone.utc) - timedelta(days=10),
            ))
            await db.commit()

        pref = seed["pref"]
        event = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_renov",
            pi_id=f"pi_{pref}_renov",
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        assert (await _post(client, event)).status_code == 200

        mats = await _matriculas(seed["aluno_id"])
        assert len(mats) == 1  # renovou, não duplicou
        assert mats[0].status == StatusMatricula.ativo
        assert mats[0].data_expiracao > datetime.now(timezone.utc) + timedelta(
            days=seed["validade_dias"] - 1
        )

    async def test_gateway_desconhecido_404(self, client: AsyncClient):
        resp = await client.post("/api/v1/webhooks/pagamento/foobar", content=b"{}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "GATEWAY_DESCONHECIDO"

    async def test_mercadopago_nao_implementado_501(self, client: AsyncClient):
        resp = await client.post("/api/v1/webhooks/pagamento/mercadopago", content=b"{}")
        assert resp.status_code == 501
        assert resp.json()["error"]["code"] == "GATEWAY_NAO_IMPLEMENTADO"
