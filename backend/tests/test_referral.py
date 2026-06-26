"""Indique-e-ganhe: atribuição no cadastro + recompensa (cupons p/ ambos)."""
import asyncio
import uuid

from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.models import Aluno, Cupom, Indicacao

SENHA = "SenhaForte123!"


async def _limpar_alunos(pref: str) -> None:
    async with AsyncSessionLocal() as db:
        alunos = (
            await db.execute(select(Aluno).where(Aluno.email.like(f"%{pref}%")))
        ).scalars().all()
        ids = [a.id for a in alunos]
        if ids:
            # cupons de recompensa apontam p/ aluno (SET NULL não apaga) — remove antes
            await db.execute(delete(Cupom).where(Cupom.aluno_id.in_(ids)))
            # indicacoes cascateiam no delete do aluno (FK CASCADE)
            for a in alunos:
                await db.delete(a)
            await db.commit()


class TestReferralCadastro:
    async def test_cadastro_com_indicacao_cria_vinculo(self, client: AsyncClient):
        pref = uuid.uuid4().hex[:8]
        try:
            # indicador se cadastra e pega o próprio código
            r1 = await client.post(
                "/api/v1/auth/register",
                json={"nome": "Indicador", "email": f"ind_{pref}@rodelcar.dev", "senha": SENHA},
            )
            assert r1.status_code == 201
            h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
            codigo = (await client.get("/api/v1/me/indicacoes", headers=h1)).json()["codigo"]
            assert codigo and len(codigo) >= 6

            # indicado se cadastra COM o código
            r2 = await client.post(
                "/api/v1/auth/register",
                json={
                    "nome": "Indicado", "email": f"indo_{pref}@rodelcar.dev",
                    "senha": SENHA, "codigo_indicacao": codigo,
                },
            )
            assert r2.status_code == 201

            # indicador agora tem 1 indicação (pendente)
            d = (await client.get("/api/v1/me/indicacoes", headers=h1)).json()
            assert d["total_indicados"] == 1
            assert d["total_recompensados"] == 0
            assert d["cupons"] == []
        finally:
            await _limpar_alunos(pref)

    async def test_cadastro_codigo_invalido_nao_bloqueia(self, client: AsyncClient):
        pref = uuid.uuid4().hex[:8]
        try:
            r = await client.post(
                "/api/v1/auth/register",
                json={
                    "nome": "Solo", "email": f"solo_{pref}@rodelcar.dev",
                    "senha": SENHA, "codigo_indicacao": "NAOEXISTE9",
                },
            )
            assert r.status_code == 201  # cadastro segue mesmo com código inválido
            h = {"Authorization": f"Bearer {r.json()['access_token']}"}
            # tem código próprio e nenhuma indicação recebida
            d = (await client.get("/api/v1/me/indicacoes", headers=h)).json()
            assert d["codigo"] and d["total_indicados"] == 0
        finally:
            await _limpar_alunos(pref)


class TestReferralRecompensa:
    async def test_recompensa_gera_cupons_para_ambos(self, monkeypatch):
        from app.core import referral

        async def fake_criar(codigo, tipo, valor, **kw):
            return (f"coup_{codigo}", f"promo_{codigo}")

        monkeypatch.setattr(referral, "criar_cupom_stripe", fake_criar)
        monkeypatch.setattr(referral, "stripe_ativo", lambda: True)

        pref = uuid.uuid4().hex[:8]
        try:
            async with AsyncSessionLocal() as db:
                a = Aluno(
                    nome="Ind", email=f"ra_{pref}@rodelcar.dev", senha_hash="x",
                    codigo_indicacao=f"R{pref[:7].upper()}",
                )
                b = Aluno(nome="Indo", email=f"rb_{pref}@rodelcar.dev", senha_hash="x")
                db.add_all([a, b])
                await db.flush()
                ind = Indicacao(
                    indicador_id=a.id, indicado_id=b.id, status="compra_confirmada"
                )
                db.add(ind)
                await db.commit()
                ind_id, aid, bid = ind.id, a.id, b.id

            async with AsyncSessionLocal() as db:
                ok = await referral.processar_recompensa(db, ind_id)
            assert ok is True

            async with AsyncSessionLocal() as db:
                ind = await db.get(Indicacao, ind_id)
                assert ind.status == "recompensado"
                assert ind.cupom_indicador_id and ind.cupom_indicado_id
                cupons = (
                    await db.execute(
                        select(Cupom).where(Cupom.aluno_id.in_([aid, bid]))
                    )
                ).scalars().all()
                assert len(cupons) == 2
                assert all(c.tipo == "percentual" and float(c.valor) == 10.0 for c in cupons)

            # idempotente: rechamar não duplica (status já != compra_confirmada)
            async with AsyncSessionLocal() as db:
                assert await referral.processar_recompensa(db, ind_id) is False
        finally:
            await _limpar_alunos(pref)

    async def test_recompensa_concorrente_nao_duplica(self, monkeypatch):
        """Lock de linha (with_for_update): webhook × job concorrentes sobre a MESMA
        indicação geram só UM par de cupons (não 4). Sem o lock, ambos passariam
        pela guarda de status e criariam cupons em dobro."""
        from app.core import referral

        async def fake_criar(codigo, tipo, valor, **kw):
            return (f"coup_{codigo}", f"promo_{codigo}")

        monkeypatch.setattr(referral, "criar_cupom_stripe", fake_criar)
        monkeypatch.setattr(referral, "stripe_ativo", lambda: True)

        pref = uuid.uuid4().hex[:8]
        try:
            async with AsyncSessionLocal() as db:
                a = Aluno(
                    nome="Ind", email=f"rca_{pref}@rodelcar.dev", senha_hash="x",
                    codigo_indicacao=f"C{pref[:7].upper()}",
                )
                b = Aluno(nome="Indo", email=f"rcb_{pref}@rodelcar.dev", senha_hash="x")
                db.add_all([a, b])
                await db.flush()
                ind = Indicacao(
                    indicador_id=a.id, indicado_id=b.id, status="compra_confirmada"
                )
                db.add(ind)
                await db.commit()
                ind_id, aid, bid = ind.id, a.id, b.id

            # Duas SESSÕES distintas processam a MESMA indicação em paralelo.
            async def run():
                async with AsyncSessionLocal() as db:
                    return await referral.processar_recompensa(db, ind_id)

            r1, r2 = await asyncio.gather(run(), run())
            assert sorted([r1, r2]) == [False, True]  # só um recompensou

            async with AsyncSessionLocal() as db:
                cupons = (
                    await db.execute(
                        select(Cupom).where(Cupom.aluno_id.in_([aid, bid]))
                    )
                ).scalars().all()
                assert len(cupons) == 2  # 2 no total (não 4)
        finally:
            await _limpar_alunos(pref)
