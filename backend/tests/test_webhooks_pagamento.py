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


def _invoice_event(
    tipo: str,
    *,
    event_id: str,
    invoice_id: str,
    sub_id: str,
    aluno_id: str,
    customer: str = "cus_test",
    amount_paid: int = 4990,
    period_end: int | None = None,
    formato: str = "atual",
) -> dict:
    """Invoice nos DOIS formatos da API Stripe.

    `atual` (basil/dahlia, 2025+): assinatura em `parent.subscription_details`.
    `legado` (<2025): `subscription` na raiz + `subscription_details`.
    """
    if period_end is None:
        period_end = int(time.time()) + 30 * 86400
    obj: dict = {
        "id": invoice_id,
        "object": "invoice",
        "customer": customer,
        "amount_paid": amount_paid,
        "amount_due": amount_paid,
        "lines": {"data": [{"period": {"end": period_end}}]},
    }
    if formato == "legado":
        obj["subscription"] = sub_id
        obj["subscription_details"] = {"metadata": {"app_user_id": aluno_id}}
    else:
        obj["parent"] = {
            "type": "subscription_details",
            "subscription_details": {
                "subscription": sub_id,
                "metadata": {"app_user_id": aluno_id},
            },
        }
    return {"id": event_id, "type": tipo, "data": {"object": obj}}


def _sub_event(tipo: str, *, event_id: str, sub_id: str) -> dict:
    return {
        "id": event_id,
        "type": tipo,
        "data": {"object": {"id": sub_id, "object": "subscription"}},
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

    async def test_evento_test_mode_ignorado_em_producao(
        self, client: AsyncClient, seed, monkeypatch
    ):
        """Em produção, evento com livemode!=true (test-mode) não concede acesso."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        pref = seed["pref"]
        event = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_tm",
            pi_id=f"pi_{pref}_tm",
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        event["livemode"] = False  # test-mode
        resp = await _post(client, event)
        assert resp.status_code == 200  # 200 p/ o Stripe não reentregar
        assert len(await _pagamentos(seed["aluno_id"])) == 0
        assert len(await _matriculas(seed["aluno_id"])) == 0

    async def test_corpo_grande_demais_413(self, client: AsyncClient, monkeypatch):
        """Corpo acima do teto é rejeitado antes do parse/verificação (DoS)."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        body = "x" * (256 * 1024 + 16)
        resp = await client.post(
            URL, content=body, headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "PAYLOAD_GRANDE_DEMAIS"

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

    async def test_pagamento_falho_grava_recusado_sem_matricula(
        self, client: AsyncClient, seed, monkeypatch
    ):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        ev = _session_event(
            "checkout.session.async_payment_failed",
            event_id=f"evt_{pref}_fail", pi_id=f"pi_{pref}_fail",
            aluno_id=seed["aluno_id"], curso_slug=seed["curso_slug"],
            payment_status="unpaid",
        )
        assert (await _post(client, ev)).status_code == 200
        pags = await _pagamentos(seed["aluno_id"])
        assert len(pags) == 1 and pags[0].status == StatusPagamento.recusado
        assert len(await _matriculas(seed["aluno_id"])) == 0

    async def test_falha_nao_rebaixa_aprovado(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        pi = f"pi_{pref}_keep"
        ok = _session_event(
            "checkout.session.completed", event_id=f"evt_{pref}_ok", pi_id=pi,
            aluno_id=seed["aluno_id"], curso_slug=seed["curso_slug"],
        )
        assert (await _post(client, ok)).status_code == 200
        # falha tardia do MESMO PaymentIntent não pode rebaixar o aprovado
        fail = _session_event(
            "checkout.session.async_payment_failed", event_id=f"evt_{pref}_late", pi_id=pi,
            aluno_id=seed["aluno_id"], curso_slug=seed["curso_slug"], payment_status="unpaid",
        )
        assert (await _post(client, fail)).status_code == 200
        pags = [p for p in await _pagamentos(seed["aluno_id"]) if p.gateway_transaction_id == pi]
        assert len(pags) == 1 and pags[0].status == StatusPagamento.aprovado
        assert len(await _matriculas(seed["aluno_id"])) == 1

    async def test_evento_sem_id_recusado_400(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        ev = _session_event(
            "checkout.session.completed", event_id="", pi_id=f"pi_{seed['pref']}_noid",
            aluno_id=seed["aluno_id"], curso_slug=seed["curso_slug"],
        )
        resp = await _post(client, ev)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "EVENTO_SEM_ID"
        assert len(await _matriculas(seed["aluno_id"])) == 0

    async def test_compra_envia_email_uma_vez(
        self, client: AsyncClient, seed, monkeypatch
    ):
        """Compra aprovada dispara 1 e-mail de confirmação; reentrega não duplica."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        import app.routers.webhooks_pagamento as wp

        enviados: list[tuple[str, str]] = []

        async def fake_email(para, assunto, corpo, *, log_ref="?"):
            enviados.append((para, assunto))
            return "fake-id"

        monkeypatch.setattr(wp, "enviar_email_bruto", fake_email)
        pref = seed["pref"]
        event = _session_event(
            "checkout.session.completed",
            event_id=f"evt_{pref}_mail",
            pi_id=f"pi_{pref}_mail",
            aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        )
        await _post(client, event)
        await _post(client, event)  # reentrega do mesmo evento → no-op, sem 2º e-mail
        assert len(enviados) == 1
        assert pref in enviados[0][0]  # foi para o e-mail do aluno
        assert "Compra confirmada" in enviados[0][1]

    async def test_payload_nao_guarda_pii(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        ev = _session_event(
            "checkout.session.completed", event_id=f"evt_{pref}_pii", pi_id=f"pi_{pref}_pii",
            aluno_id=seed["aluno_id"], curso_slug=seed["curso_slug"],
        )
        # Stripe manda nome/e-mail do cliente — não devem ser persistidos (LGPD).
        ev["data"]["object"]["customer_details"] = {
            "email": "vitima@exemplo.com", "name": "Fulano de Tal",
        }
        ev["data"]["object"]["customer_email"] = "vitima@exemplo.com"
        assert (await _post(client, ev)).status_code == 200
        blob = json.dumps((await _pagamentos(seed["aluno_id"]))[0].payload)
        assert "vitima@exemplo.com" not in blob
        assert "customer_details" not in blob
        assert "Fulano" not in blob


async def _matricula_do_curso(aluno_id: str, curso_id: str) -> Matricula | None:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(
                select(Matricula).where(
                    Matricula.aluno_id == uuid.UUID(aluno_id),
                    Matricula.curso_id == uuid.UUID(curso_id),
                )
            )
        ).scalar_one_or_none()


class TestWebhookAssinatura:
    async def test_invoice_paid_libera_catalogo(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        sub = f"sub_{pref}"
        period_end = int(time.time()) + 30 * 86400
        ev = _invoice_event(
            "invoice.paid",
            event_id=f"evt_{pref}_inv1",
            invoice_id=f"in_{pref}_1",
            sub_id=sub,
            aluno_id=seed["aluno_id"],
            period_end=period_end,
        )
        assert (await _post(client, ev)).status_code == 200

        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat is not None
        assert mat.status == StatusMatricula.ativo
        assert mat.stripe_subscription_id == sub
        esperado = datetime.fromtimestamp(period_end, tz=timezone.utc)
        assert abs((mat.data_expiracao - esperado).total_seconds()) < 5

        pags = await _pagamentos(seed["aluno_id"])
        assert any(
            p.gateway_transaction_id == f"in_{pref}_1" and p.status == StatusPagamento.aprovado
            for p in pags
        )

    async def test_avulso_sobre_assinatura_sobrevive_ao_cancelamento(
        self, client: AsyncClient, seed, monkeypatch
    ):
        """Compra avulsa por cima de assinatura desamarra a matrícula: cancelar a
        assinatura depois NÃO pode expirar o curso pago avulso."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        sub = f"sub_{pref}_mix"

        # 1) Assinatura libera o catálogo (matrícula do curso seed fica com o sub).
        await _post(client, _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_mix1", invoice_id=f"in_{pref}_mix",
            sub_id=sub, aluno_id=seed["aluno_id"],
        ))
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat is not None and mat.stripe_subscription_id == sub

        # 2) Compra AVULSA do mesmo curso → renova e desamarra da assinatura.
        await _post(client, _session_event(
            "checkout.session.completed", event_id=f"evt_{pref}_mix2",
            pi_id=f"pi_{pref}_mix", aluno_id=seed["aluno_id"],
            curso_slug=seed["curso_slug"],
        ))
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat.stripe_subscription_id is None

        # 3) Cancelamento da assinatura não derruba o curso comprado avulso.
        await _post(client, _sub_event(
            "customer.subscription.deleted", event_id=f"evt_{pref}_mix3", sub_id=sub
        ))
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat.status == StatusMatricula.ativo

    async def test_assinatura_sobre_avulso_preserva_o_avulso(
        self, client: AsyncClient, seed, monkeypatch
    ):
        """Ordem AVULSO→ASSINATURA: a fatura NÃO encurta a vigência longa do avulso,
        NÃO re-amarra à assinatura e NÃO troca o pagamento. Cancelar a assinatura
        depois NÃO expira o curso pago avulso."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        sub = f"sub_{pref}_av"

        # 1) Compra AVULSA do curso (validade 365d, sem assinatura).
        await _post(client, _session_event(
            "checkout.session.completed", event_id=f"evt_{pref}_av1",
            pi_id=f"pi_{pref}_av", aluno_id=seed["aluno_id"], curso_slug=seed["curso_slug"],
        ))
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat.stripe_subscription_id is None and mat.pagamento_id is not None
        exp_avulso = mat.data_expiracao
        pag_avulso = mat.pagamento_id

        # 2) Assinatura libera o catálogo (ciclo curto ~30d).
        period_end = int(time.time()) + 30 * 86400
        await _post(client, _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_av2", invoice_id=f"in_{pref}_av",
            sub_id=sub, aluno_id=seed["aluno_id"], period_end=period_end,
        ))
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        # Preserva o avulso: sem re-amarrar, sem encurtar, sem trocar o pagamento.
        assert mat.stripe_subscription_id is None
        assert mat.pagamento_id == pag_avulso
        assert mat.data_expiracao == exp_avulso  # max() manteve a vigência de 365d

        # 3) Cancelar a assinatura NÃO expira o curso pago avulso.
        await _post(client, _sub_event(
            "customer.subscription.deleted", event_id=f"evt_{pref}_av3", sub_id=sub,
        ))
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat.status == StatusMatricula.ativo

    async def test_invoice_paid_formato_legado(self, client: AsyncClient, seed, monkeypatch):
        """Compat: invoice no formato antigo (`subscription` na raiz) segue funcionando."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        sub = f"sub_{pref}_leg"
        ev = _invoice_event(
            "invoice.paid",
            event_id=f"evt_{pref}_leg",
            invoice_id=f"in_{pref}_leg",
            sub_id=sub,
            aluno_id=seed["aluno_id"],
            formato="legado",
        )
        assert (await _post(client, ev)).status_code == 200
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat is not None
        assert mat.status == StatusMatricula.ativo
        assert mat.stripe_subscription_id == sub

    async def test_invoice_paid_renova_expiracao(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        sub = f"sub_{pref}"
        fim1 = int(time.time()) + 30 * 86400
        fim2 = int(time.time()) + 60 * 86400
        await _post(client, _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_r1", invoice_id=f"in_{pref}_r1",
            sub_id=sub, aluno_id=seed["aluno_id"], period_end=fim1,
        ))
        await _post(client, _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_r2", invoice_id=f"in_{pref}_r2",
            sub_id=sub, aluno_id=seed["aluno_id"], period_end=fim2,
        ))
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat is not None
        esperado = datetime.fromtimestamp(fim2, tz=timezone.utc)
        assert abs((mat.data_expiracao - esperado).total_seconds()) < 5

    async def test_subscription_deleted_revoga(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        sub = f"sub_{pref}"
        await _post(client, _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_d1", invoice_id=f"in_{pref}_d1",
            sub_id=sub, aluno_id=seed["aluno_id"],
        ))
        assert (await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])).status == StatusMatricula.ativo

        resp = await _post(client, _sub_event(
            "customer.subscription.deleted", event_id=f"evt_{pref}_del", sub_id=sub,
        ))
        assert resp.status_code == 200
        mat = await _matricula_do_curso(seed["aluno_id"], seed["curso_id"])
        assert mat.status == StatusMatricula.expirado

    async def test_assinatura_envia_boas_vindas_so_na_criacao(
        self, client: AsyncClient, seed, monkeypatch
    ):
        """invoice.paid com billing_reason=subscription_create manda boas-vindas;
        renovação (subscription_cycle) não reenvia."""
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        import app.routers.webhooks_pagamento as wp

        enviados: list[str] = []

        async def fake_email(para, assunto, corpo, *, log_ref="?"):
            enviados.append(assunto)
            return "fake-id"

        monkeypatch.setattr(wp, "enviar_email_bruto", fake_email)
        pref = seed["pref"]
        # 1ª fatura (criação) → boas-vindas
        ev1 = _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_sc", invoice_id=f"in_{pref}_sc",
            sub_id=f"sub_{pref}_sc", aluno_id=seed["aluno_id"],
        )
        ev1["data"]["object"]["billing_reason"] = "subscription_create"
        await _post(client, ev1)
        # renovação → sem e-mail
        ev2 = _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_cy", invoice_id=f"in_{pref}_cy",
            sub_id=f"sub_{pref}_sc", aluno_id=seed["aluno_id"],
        )
        ev2["data"]["object"]["billing_reason"] = "subscription_cycle"
        await _post(client, ev2)
        assert len(enviados) == 1
        assert "Assinatura" in enviados[0]

    async def test_invoice_paid_duplicado(self, client: AsyncClient, seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)
        pref = seed["pref"]
        ev = _invoice_event(
            "invoice.paid", event_id=f"evt_{pref}_dup", invoice_id=f"in_{pref}_dup",
            sub_id=f"sub_{pref}", aluno_id=seed["aluno_id"],
        )
        await _post(client, ev)
        await _post(client, ev)  # mesmo event.id → no-op
        pags = await _pagamentos(seed["aluno_id"])
        assert sum(1 for p in pags if p.gateway_transaction_id == f"in_{pref}_dup") == 1
