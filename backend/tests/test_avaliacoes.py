"""Avaliações (reviews) de curso: fluxo do aluno + moderação do admin."""
import uuid

import pytest_asyncio
from httpx import AsyncClient

from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Admin, PapelAdmin


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> dict:
    email = f"admin_av_{uuid.uuid4().hex[:8]}@rodelcar.dev"
    async with AsyncSessionLocal() as s:
        adm = Admin(
            nome="Moderador",
            email=email,
            senha_hash=hash_password("AdminTest123!"),
            papel=PapelAdmin.administrador,
            ativo=True,
        )
        s.add(adm)
        await s.commit()
        aid = adm.id
    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": email, "senha": "AdminTest123!"},
    )
    yield {"Authorization": f"Bearer {resp.json()['access_token']}"}
    async with AsyncSessionLocal() as s:
        obj = await s.get(Admin, aid)
        if obj:
            await s.delete(obj)
            await s.commit()


# ── Fluxo do aluno ────────────────────────────────────────────────────────────
class TestAvaliacaoAluno:
    async def test_sem_matricula_403(self, client, auth_headers, test_data):
        resp = await client.post(
            f"/api/v1/cursos/{test_data['curso_sem_mat_slug']}/avaliacoes",
            json={"nota": 5, "texto": "ótimo"},
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PRECISA_MATRICULA"

    async def test_sem_token_401(self, client, test_data):
        resp = await client.post(
            f"/api/v1/cursos/{test_data['curso_ativo_slug']}/avaliacoes",
            json={"nota": 5},
        )
        assert resp.status_code == 401

    async def test_nota_invalida_422(self, client, auth_headers, test_data):
        resp = await client.post(
            f"/api/v1/cursos/{test_data['curso_ativo_slug']}/avaliacoes",
            json={"nota": 9},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_curso_inexistente_404(self, client):
        resp = await client.get("/api/v1/cursos/nao-existe-xyz/avaliacoes")
        assert resp.status_code == 404

    async def test_criar_listar_e_upsert(self, client, auth_headers, test_data):
        slug = test_data["curso_ativo_slug"]
        # cria
        r = await client.post(
            f"/api/v1/cursos/{slug}/avaliacoes",
            json={"nota": 4, "texto": "Muito bom"},
            headers=auth_headers,
        )
        assert r.status_code == 200 and r.json()["nota"] == 4

        # lista pública (aprovado por padrão)
        d = (await client.get(f"/api/v1/cursos/{slug}/avaliacoes")).json()
        assert d["total"] == 1
        assert d["media"] == 4.0
        assert d["items"][0]["nota"] == 4
        assert d["items"][0]["autor"]  # nome abreviado presente

        # re-avaliar = upsert (não duplica), atualiza nota
        r2 = await client.post(
            f"/api/v1/cursos/{slug}/avaliacoes",
            json={"nota": 2, "texto": "mudei de ideia"},
            headers=auth_headers,
        )
        assert r2.status_code == 200 and r2.json()["nota"] == 2
        d2 = (await client.get(f"/api/v1/cursos/{slug}/avaliacoes")).json()
        assert d2["total"] == 1 and d2["media"] == 2.0

        # minha avaliação reflete o último valor
        minha = (
            await client.get(
                f"/api/v1/cursos/{slug}/avaliacoes/minha", headers=auth_headers
            )
        ).json()
        assert minha["nota"] == 2

    async def test_aggregate_rating_no_detalhe(self, client, auth_headers, test_data):
        slug = test_data["curso_ativo_slug"]
        await client.post(
            f"/api/v1/cursos/{slug}/avaliacoes",
            json={"nota": 5},
            headers=auth_headers,
        )
        d = (await client.get(f"/api/v1/cursos/{slug}")).json()
        assert d["rating_count"] >= 1
        assert d["rating_medio"] is not None


# ── Moderação pelo admin ──────────────────────────────────────────────────────
class TestAvaliacaoModeracao:
    async def test_listar_ocultar_e_excluir(
        self, client, auth_headers, admin_token, test_data
    ):
        slug = test_data["curso_ativo_slug"]
        await client.post(
            f"/api/v1/cursos/{slug}/avaliacoes",
            json={"nota": 5, "texto": "Conteúdo a moderar"},
            headers=auth_headers,
        )
        # admin lista e encontra (curso de teste tem título fixo no conftest)
        lst = (await client.get("/api/v1/admin/avaliacoes", headers=admin_token)).json()
        alvo = next(a for a in lst if a["curso_titulo"] == "Curso Ativo Teste")
        assert alvo["aluno_nome"]

        # oculta (Pendente) → some da lista pública
        patch = await client.patch(
            f"/api/v1/admin/avaliacoes/{alvo['id']}",
            json={"status": "Pendente"},
            headers=admin_token,
        )
        assert patch.status_code == 200 and patch.json()["status"] == "Pendente"
        pub = (await client.get(f"/api/v1/cursos/{slug}/avaliacoes")).json()
        assert pub["total"] == 0

        # exclui
        dele = await client.delete(
            f"/api/v1/admin/avaliacoes/{alvo['id']}", headers=admin_token
        )
        assert dele.status_code == 204

    async def test_moderacao_exige_admin(self, client, auth_headers):
        # token de aluno não acessa rota de admin
        resp = await client.get("/api/v1/admin/avaliacoes", headers=auth_headers)
        assert resp.status_code in (401, 403)
