"""Cancelamento com reembolso (POST /api/v1/me/matriculas/{id}/cancelar).

Direito de arrependimento: 7 dias após o pagamento. Stripe stubada (sem rede).
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
import stripe
from httpx import AsyncClient
from sqlalchemy import delete, select

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
)

SENHA = "Cancel123!"


@pytest.fixture(autouse=True)
def stripe_stub(monkeypatch):
    """Stubs: Refund/Subscription/InvoicePayment — nenhum teste toca a API real."""
    chamadas: dict[str, list] = {"refund": [], "sub_cancel": []}

    class _Stub:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    def refund_create(**kw):
        chamadas["refund"].append(kw)
        return _Stub(id=f"re_stub_{len(chamadas['refund'])}")

    def sub_cancel(sub_id, **kw):
        chamadas["sub_cancel"].append(sub_id)
        return _Stub(id=sub_id, status="canceled")

    def invoice_payment_list(**kw):
        # shape real da API 2025+ (testado ao vivo): data[].payment.payment_intent
        return {"data": [{"payment": {"type": "payment_intent", "payment_intent": "pi_da_invoice"}}]}

    monkeypatch.setattr(stripe.Refund, "create", refund_create)
    monkeypatch.setattr(stripe.Subscription, "cancel", sub_cancel)
    monkeypatch.setattr(stripe.InvoicePayment, "list", invoice_payment_list)
    return chamadas


async def _criar_compra(
    db, aluno_id, *, pref: str, sufixo: str, sub_id: str | None = None,
    pago_ha_dias: int = 0,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Curso + Pagamento aprovado + Matricula ativa. Retorna (matricula_id, curso_id)."""
    curso = Curso(
        slug=f"cancel-{sufixo}-{pref}",
        titulo=f"Curso Cancel {sufixo}",
        tipo=TipoCurso.avulso,
        preco=Decimal("100.00"),
        validade_dias=365,
    )
    db.add(curso)
    await db.flush()
    pag = Pagamento(
        aluno_id=aluno_id,
        gateway="stripe",
        gateway_transaction_id=(f"in_{pref}_{sufixo}" if sub_id else f"pi_{pref}_{sufixo}"),
        valor=Decimal("100.00"),
        status=StatusPagamento.aprovado,
        payload={},
        criado_em=datetime.now(timezone.utc) - timedelta(days=pago_ha_dias),
    )
    db.add(pag)
    await db.flush()
    mat = Matricula(
        aluno_id=aluno_id,
        curso_id=curso.id,
        pagamento_id=pag.id,
        stripe_subscription_id=sub_id,
        status=StatusMatricula.ativo,
        data_expiracao=datetime.now(timezone.utc) + timedelta(days=365),
    )
    db.add(mat)
    await db.flush()
    return mat.id, curso.id


@pytest_asyncio.fixture
async def cancel_seed(client: AsyncClient):
    pref = uuid.uuid4().hex[:8]
    email = f"cancel_{pref}@rodelcar.dev"
    async with AsyncSessionLocal() as db:
        aluno = Aluno(nome="Cancel Tester", email=email, senha_hash=hash_password(SENHA))
        db.add(aluno)
        await db.flush()
        aluno_id = aluno.id

        mat_ok, curso_ok = await _criar_compra(db, aluno_id, pref=pref, sufixo="ok")
        mat_velha, curso_velho = await _criar_compra(
            db, aluno_id, pref=pref, sufixo="velha", pago_ha_dias=8
        )
        sub = f"sub_{pref}"
        mat_sub1, curso_sub1 = await _criar_compra(
            db, aluno_id, pref=pref, sufixo="sub1", sub_id=sub
        )
        # 2ª matrícula da MESMA assinatura (catálogo) — sem pagamento próprio
        curso2 = Curso(
            slug=f"cancel-sub2-{pref}", titulo="Curso Cancel sub2",
            tipo=TipoCurso.avulso, preco=Decimal("100.00"), validade_dias=365,
        )
        db.add(curso2)
        await db.flush()
        mat2 = Matricula(
            aluno_id=aluno_id, curso_id=curso2.id, stripe_subscription_id=sub,
            status=StatusMatricula.ativo,
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=365),
        )
        db.add(mat2)
        await db.flush()
        cursos = [curso_ok, curso_velho, curso_sub1, curso2.id]
        data = {
            "pref": pref,
            "aluno_id": str(aluno_id),
            "mat_ok": str(mat_ok),
            "mat_velha": str(mat_velha),
            "mat_sub": str(mat_sub1),
            "mat_sub2": str(mat2.id),
            "sub": sub,
            "cursos": [str(c) for c in cursos],
        }
        await db.commit()

    resp = await client.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
    data["headers"] = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    yield data

    aid = uuid.UUID(data["aluno_id"])
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Matricula).where(Matricula.aluno_id == aid))
        await db.execute(delete(Pagamento).where(Pagamento.aluno_id == aid))
        await db.execute(
            delete(Curso).where(Curso.id.in_([uuid.UUID(c) for c in data["cursos"]]))
        )
        await db.execute(delete(Aluno).where(Aluno.id == aid))
        await db.commit()


async def _mat(mat_id: str) -> Matricula:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(select(Matricula).where(Matricula.id == uuid.UUID(mat_id)))
        ).scalar_one()


class TestCancelamento:
    async def test_avulso_dentro_do_prazo_reembolsa(
        self, client: AsyncClient, cancel_seed, stripe_stub
    ):
        resp = await client.post(
            f"/api/v1/me/matriculas/{cancel_seed['mat_ok']}/cancelar",
            headers=cancel_seed["headers"],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["reembolsado"] is True
        assert body["assinatura_cancelada"] is False
        assert body["cursos_revogados"] == 1
        # Refund do PI da compra; matrícula expirada; pagamento estornado.
        assert stripe_stub["refund"][-1]["payment_intent"].startswith("pi_")
        mat = await _mat(cancel_seed["mat_ok"])
        assert mat.status == StatusMatricula.expirado
        async with AsyncSessionLocal() as db:
            pag = (
                await db.execute(
                    select(Pagamento).where(Pagamento.id == mat.pagamento_id)
                )
            ).scalar_one()
            assert pag.status == StatusPagamento.estornado

    async def test_fora_do_prazo_400(self, client: AsyncClient, cancel_seed):
        resp = await client.post(
            f"/api/v1/me/matriculas/{cancel_seed['mat_velha']}/cancelar",
            headers=cancel_seed["headers"],
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "FORA_DO_PRAZO"

    async def test_matricula_alheia_404(
        self, client: AsyncClient, cancel_seed, auth_headers
    ):
        # auth_headers = aluno padrão dos testes (outro dono)
        resp = await client.post(
            f"/api/v1/me/matriculas/{cancel_seed['mat_ok']}/cancelar",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_assinatura_cancela_e_revoga_catalogo(
        self, client: AsyncClient, cancel_seed, stripe_stub
    ):
        resp = await client.post(
            f"/api/v1/me/matriculas/{cancel_seed['mat_sub']}/cancelar",
            headers=cancel_seed["headers"],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["assinatura_cancelada"] is True
        assert body["cursos_revogados"] == 2
        assert stripe_stub["sub_cancel"] == [cancel_seed["sub"]]
        # PI veio do invoice_payments (API nova)
        assert stripe_stub["refund"][-1]["payment_intent"] == "pi_da_invoice"
        assert (await _mat(cancel_seed["mat_sub"])).status == StatusMatricula.expirado
        assert (await _mat(cancel_seed["mat_sub2"])).status == StatusMatricula.expirado

    async def test_listagem_expoe_elegibilidade(
        self, client: AsyncClient, cancel_seed
    ):
        resp = await client.get("/api/v1/me/matriculas", headers=cancel_seed["headers"])
        assert resp.status_code == 200
        por_id = {m["id"]: m for m in resp.json()["items"]}
        ok = por_id[cancel_seed["mat_ok"]]
        assert ok["cancelavel"] is True and ok["origem"] == "avulsa"
        assert ok["cancelavel_ate"] is not None
        velha = por_id[cancel_seed["mat_velha"]]
        assert velha["cancelavel"] is False
        sub = por_id[cancel_seed["mat_sub"]]
        assert sub["origem"] == "assinatura" and sub["cancelavel"] is True
        # matrícula do catálogo sem pagamento próprio: não cancelável diretamente
        sub2 = por_id[cancel_seed["mat_sub2"]]
        assert sub2["cancelavel"] is False
