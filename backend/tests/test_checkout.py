"""Testes do checkout avulso (POST /api/v1/checkout/avulso).

Mocka as chamadas de saída do Stripe (Session.create / Customer.create) — não toca
a API real. Verifica criação da sessão, persistência do customer e os erros.
"""
import uuid
from decimal import Decimal

import pytest_asyncio
import stripe
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Aluno, Curso, PlanoAssinatura, TipoCurso

URL = "/api/v1/checkout/avulso"
SENHA = "Checkout123!"


class _Stub:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _fake_session_create(**kwargs):
    return _Stub(id="cs_test_123", url="https://checkout.stripe.test/cs_test_123")


def _fake_customer_create(**kwargs):
    return _Stub(id="cus_test_123")


@pytest_asyncio.fixture
async def checkout_seed(client: AsyncClient):
    """Aluno (logado) + curso com price_id. Retorna headers, slug e aluno_id."""
    pref = uuid.uuid4().hex[:8]
    email = f"checkout_{pref}@rodelcar.dev"
    async with AsyncSessionLocal() as db:
        aluno = Aluno(nome="Checkout Tester", email=email, senha_hash=hash_password(SENHA))
        db.add(aluno)
        await db.flush()
        curso = Curso(
            slug=f"checkout-{pref}",
            titulo="Curso Checkout",
            tipo=TipoCurso.avulso,
            preco=Decimal("497.00"),
            validade_dias=365,
            stripe_price_id=f"price_{pref}",
        )
        curso_sem_price = Curso(
            slug=f"semprice-{pref}",
            titulo="Curso Sem Price",
            tipo=TipoCurso.avulso,
            preco=Decimal("100.00"),
            validade_dias=365,
        )
        plano = PlanoAssinatura(
            nome=f"Mensal {pref}",
            intervalo="mensal",
            stripe_price_id=f"price_sub_{pref}",
            preco=Decimal("49.90"),
            status="Ativo",
        )
        db.add_all([curso, curso_sem_price, plano])
        await db.flush()
        await db.commit()
        data = {
            "aluno_id": str(aluno.id),
            "curso_id": str(curso.id),
            "curso_slug": curso.slug,
            "curso_sem_price_id": str(curso_sem_price.id),
            "curso_sem_price_slug": curso_sem_price.slug,
            "plano_id": str(plano.id),
            "plano_preco": plano.preco,
        }

    resp = await client.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
    data["headers"] = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    yield data

    aid = uuid.UUID(data["aluno_id"])
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(Curso).where(
                Curso.id.in_([uuid.UUID(data["curso_id"]), uuid.UUID(data["curso_sem_price_id"])])
            )
        )
        await db.execute(
            delete(PlanoAssinatura).where(PlanoAssinatura.id == uuid.UUID(data["plano_id"]))
        )
        await db.execute(delete(Aluno).where(Aluno.id == aid))
        await db.commit()


class TestCheckoutAvulso:
    async def test_cria_sessao_e_persiste_customer(self, client, checkout_seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        monkeypatch.setattr(stripe.checkout.Session, "create", _fake_session_create)
        monkeypatch.setattr(stripe.Customer, "create", _fake_customer_create)

        resp = await client.post(
            URL, json={"curso_slug": checkout_seed["curso_slug"]}, headers=checkout_seed["headers"]
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["checkout_url"] == "https://checkout.stripe.test/cs_test_123"
        assert body["session_id"] == "cs_test_123"

        async with AsyncSessionLocal() as db:
            aluno = (
                await db.execute(
                    select(Aluno).where(Aluno.id == uuid.UUID(checkout_seed["aluno_id"]))
                )
            ).scalar_one()
            assert aluno.stripe_customer_id == "cus_test_123"

    async def test_curso_sem_price_404(self, client, checkout_seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        resp = await client.post(
            URL,
            json={"curso_slug": checkout_seed["curso_sem_price_slug"]},
            headers=checkout_seed["headers"],
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PRECO_NAO_CONFIGURADO"

    async def test_curso_inexistente_404(self, client, checkout_seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        resp = await client.post(
            URL, json={"curso_slug": "nao-existe-xyz"}, headers=checkout_seed["headers"]
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CURSO_NAO_ENCONTRADO"

    async def test_sem_token_401(self, client: AsyncClient):
        resp = await client.post(URL, json={"curso_slug": "qualquer"})
        assert resp.status_code == 401

    async def test_fallback_card_quando_pix_indisponivel(
        self, client, checkout_seed, monkeypatch
    ):
        """Conta sem Pix (preview/convite no BR): degrada para só cartão, não bloqueia."""
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        chamadas: list[list[str]] = []

        def fake(**kwargs):
            chamadas.append(kwargs["payment_method_types"])
            if "pix" in kwargs["payment_method_types"]:
                raise stripe.error.InvalidRequestError(
                    "The payment method type provided: pix is invalid.",
                    param="payment_method_types",
                )
            return _Stub(id="cs_card_only", url="https://checkout.stripe.test/cs_card_only")

        monkeypatch.setattr(stripe.checkout.Session, "create", fake)
        monkeypatch.setattr(stripe.Customer, "create", _fake_customer_create)

        resp = await client.post(
            URL, json={"curso_slug": checkout_seed["curso_slug"]}, headers=checkout_seed["headers"]
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "cs_card_only"
        assert chamadas == [["card", "pix"], ["card"]]


class TestCheckoutAssinatura:
    async def test_assinatura_cartao_200(self, client, checkout_seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        captura: dict = {}

        def fake(**kwargs):
            captura.update(kwargs)
            return _Stub(id="cs_sub_card", url="https://checkout.stripe.test/cs_sub_card")

        monkeypatch.setattr(stripe.checkout.Session, "create", fake)
        monkeypatch.setattr(stripe.Customer, "create", _fake_customer_create)

        resp = await client.post(
            "/api/v1/checkout/assinatura-cartao",
            json={"plano_id": checkout_seed["plano_id"]},
            headers=checkout_seed["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "cs_sub_card"
        assert captura["mode"] == "subscription"
        assert captura["payment_method_types"] == ["card"]

    async def test_assinatura_pix_mandate(self, client, checkout_seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        captura: dict = {}

        def fake(**kwargs):
            captura.update(kwargs)
            return _Stub(id="cs_sub_pix", url="https://checkout.stripe.test/cs_sub_pix")

        monkeypatch.setattr(stripe.checkout.Session, "create", fake)
        monkeypatch.setattr(stripe.Customer, "create", _fake_customer_create)

        resp = await client.post(
            "/api/v1/checkout/assinatura-pix",
            json={"plano_id": checkout_seed["plano_id"]},
            headers=checkout_seed["headers"],
        )
        assert resp.status_code == 200
        assert captura["mode"] == "subscription"
        assert captura["payment_method_types"] == ["pix"]
        mandate = captura["payment_method_options"]["pix"]["mandate_options"]
        assert mandate["amount_type"] == "maximum"
        assert mandate["payment_schedule"] == "monthly"
        # teto = 2× o preço do plano, em centavos
        esperado = int(Decimal(str(checkout_seed["plano_preco"])) * 100 * 2)
        assert mandate["amount"] == esperado

    async def test_assinatura_plano_inexistente_404(self, client, checkout_seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        resp = await client.post(
            "/api/v1/checkout/assinatura-cartao",
            json={"plano_id": str(uuid.uuid4())},
            headers=checkout_seed["headers"],
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PLANO_NAO_ENCONTRADO"

    async def test_assinatura_sem_token_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/checkout/assinatura-cartao", json={"plano_id": str(uuid.uuid4())}
        )
        assert resp.status_code == 401

    async def test_assinatura_plano_inativo_404(self, client, checkout_seed, monkeypatch):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
        async with AsyncSessionLocal() as db:
            plano = (
                await db.execute(
                    select(PlanoAssinatura).where(
                        PlanoAssinatura.id == uuid.UUID(checkout_seed["plano_id"])
                    )
                )
            ).scalar_one()
            plano.status = "Inativo"
            await db.commit()
        resp = await client.post(
            "/api/v1/checkout/assinatura-cartao",
            json={"plano_id": checkout_seed["plano_id"]},
            headers=checkout_seed["headers"],
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PLANO_NAO_ENCONTRADO"
