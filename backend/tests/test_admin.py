import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import Admin, Aluno, Faq, PapelAdmin, Video

ADMIN_EMAIL = f"admin_{uuid.uuid4().hex[:8]}@rodelcar.dev"
ADMIN_PASS = "AdminTest123!"


@pytest_asyncio.fixture
async def admin_user():
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        admin = Admin(
            nome="Admin Teste",
            email=ADMIN_EMAIL,
            senha_hash=hash_password(ADMIN_PASS),
            papel=PapelAdmin.administrador,
            ativo=True,
        )
        s.add(admin)
        await s.commit()
        admin_id = admin.id
    yield {"id": str(admin_id), "email": ADMIN_EMAIL, "password": ADMIN_PASS}
    async with Session() as s:
        obj = await s.get(Admin, admin_id)
        if obj:
            await s.delete(obj)
            await s.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user: dict) -> dict:
    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin_user["email"], "senha": admin_user["password"]},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Auth do painel ────────────────────────────────────────────────────────────
class TestAdminAuth:
    async def test_login_senha_errada_retorna_401(
        self, client: AsyncClient, admin_user: dict
    ):
        resp = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": admin_user["email"], "senha": "errada"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "CREDENCIAIS_INVALIDAS"

    async def test_login_ok_e_me(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get("/api/v1/admin/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["papel"] == "Administrador"

    async def test_rota_admin_sem_token_retorna_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/videos")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "NAO_AUTENTICADO"

    async def test_token_de_aluno_nao_acessa_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Token de aluno (type=access) é rejeitado nas rotas de admin."""
        resp = await client.get("/api/v1/admin/videos", headers=auth_headers)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"

    async def test_logout_invalida_token(self, client: AsyncClient, admin_user: dict):
        """Logout incrementa token_version → o access token deixa de valer."""
        login = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": admin_user["email"], "senha": admin_user["password"]},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert (await client.get("/api/v1/admin/auth/me", headers=headers)).status_code == 200
        assert (await client.post("/api/v1/admin/auth/logout", headers=headers)).status_code == 204
        # Mesmo token, agora com tv defasado → 401.
        resp = await client.get("/api/v1/admin/auth/me", headers=headers)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"


# ── CRUD de Vídeos (fábrica _crud_router) ─────────────────────────────────────
class TestAdminVideos:
    async def test_ciclo_completo(self, client: AsyncClient, admin_headers: dict):
        # create
        resp = await client.post(
            "/api/v1/admin/videos",
            headers=admin_headers,
            json={"titulo": "Vídeo CRUD", "duracao": "05:00", "status": "Ativo"},
        )
        assert resp.status_code == 201
        vid = resp.json()
        assert vid["titulo"] == "Vídeo CRUD"
        vid_id = vid["id"]

        # list contém
        lista = (await client.get("/api/v1/admin/videos", headers=admin_headers)).json()
        assert any(v["id"] == vid_id for v in lista)

        # patch
        resp = await client.patch(
            f"/api/v1/admin/videos/{vid_id}",
            headers=admin_headers,
            json={"views": "9 mil"},
        )
        assert resp.status_code == 200
        assert resp.json()["views"] == "9 mil"

        # delete
        resp = await client.delete(
            f"/api/v1/admin/videos/{vid_id}", headers=admin_headers
        )
        assert resp.status_code == 204

        lista = (await client.get("/api/v1/admin/videos", headers=admin_headers)).json()
        assert not any(v["id"] == vid_id for v in lista)


# ── CRUD de FAQ ───────────────────────────────────────────────────────────────
class TestAdminFaq:
    async def test_cria_e_exclui(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/admin/faqs",
            headers=admin_headers,
            json={"pergunta": "Pergunta CRUD?", "resposta": "Resposta CRUD."},
        )
        assert resp.status_code == 201
        faq_id = resp.json()["id"]
        assert resp.json()["status"] == "Ativo"

        resp = await client.delete(
            f"/api/v1/admin/faqs/{faq_id}", headers=admin_headers
        )
        assert resp.status_code == 204


# ── CRUD de Alunos (campos de matrícula derivados) ────────────────────────────
class TestAdminAlunos:
    async def test_cria_aluno_com_campos_derivados(
        self, client: AsyncClient, admin_headers: dict
    ):
        email = f"novo_{uuid.uuid4().hex[:8]}@rodelcar.dev"
        resp = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={
                "nome": "Aluno Novo",
                "email": email,
                "senha": "SenhaForte123",
                "telefone": "(51) 90000-0000",
            },
        )
        assert resp.status_code == 201
        aluno = resp.json()
        aluno_id = aluno["id"]
        # sem matrícula → derivados zerados
        assert aluno["matriculas"] == 0
        assert aluno["vigencia"] is None
        assert aluno["status"] == "Inativo"

        # email duplicado → 409
        dup = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "Outro", "email": email, "senha": "SenhaForte123"},
        )
        assert dup.status_code == 409
        assert dup.json()["error"]["code"] == "EMAIL_EM_USO"

        # cleanup
        await client.delete(f"/api/v1/admin/alunos/{aluno_id}", headers=admin_headers)

    async def test_senha_curta_retorna_422(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "X", "email": "x@y.dev", "senha": "123"},
        )
        assert resp.status_code == 422


# ── RBAC: papéis Editor/Suporte têm escopo restrito ───────────────────────────
@pytest_asyncio.fixture
async def suporte_headers(client: AsyncClient) -> dict:
    email = f"suporte_{uuid.uuid4().hex[:8]}@rodelcar.dev"
    senha = "SuporteTest123!"
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        adm = Admin(
            nome="Suporte Teste",
            email=email,
            senha_hash=hash_password(senha),
            papel=PapelAdmin.suporte,
            ativo=True,
        )
        s.add(adm)
        await s.commit()
        adm_id = adm.id
    resp = await client.post(
        "/api/v1/admin/auth/login", json={"email": email, "senha": senha}
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    yield headers
    async with Session() as s:
        obj = await s.get(Admin, adm_id)
        if obj:
            await s.delete(obj)
            await s.commit()
    await engine.dispose()


class TestAdminRBAC:
    async def test_suporte_bloqueado_em_cursos(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get("/api/v1/admin/cursos", headers=suporte_headers)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PERMISSAO_NEGADA"

    async def test_suporte_bloqueado_em_administradores(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get(
            "/api/v1/admin/administradores", headers=suporte_headers
        )
        assert resp.status_code == 403

    async def test_suporte_acessa_alunos(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get("/api/v1/admin/alunos", headers=suporte_headers)
        assert resp.status_code == 200

    async def test_admin_nao_altera_proprio_papel(
        self, client: AsyncClient, admin_headers: dict, admin_user: dict
    ):
        resp = await client.patch(
            f"/api/v1/admin/administradores/{admin_user['id']}",
            headers=admin_headers,
            json={"papel": "Editor"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "AUTO_ALTERACAO_PAPEL"


# ── Planos de assinatura (Premium) ────────────────────────────────────────────
class TestAdminPlanos:
    async def test_ciclo_completo(self, client: AsyncClient, admin_headers: dict):
        pref = uuid.uuid4().hex[:8]
        # create
        resp = await client.post(
            "/api/v1/admin/planos",
            headers=admin_headers,
            json={
                "nome": f"Plano Teste {pref}",
                "intervalo": "anual",
                "stripe_price_id": f"price_adm_{pref}",
                "preco": 499.0,
            },
        )
        assert resp.status_code == 201
        plano = resp.json()
        assert plano["status"] == "Ativo"
        assert plano["stripe_price_id"] == f"price_adm_{pref}"

        # price duplicado → 409 (não 500)
        dup = await client.post(
            "/api/v1/admin/planos",
            headers=admin_headers,
            json={
                "nome": "Outro",
                "intervalo": "mensal",
                "stripe_price_id": f"price_adm_{pref}",
                "preco": 49.9,
            },
        )
        assert dup.status_code == 409
        assert dup.json()["error"]["code"] == "PRICE_EM_USO"

        # list
        lista = await client.get("/api/v1/admin/planos", headers=admin_headers)
        assert lista.status_code == 200
        assert any(p["id"] == plano["id"] for p in lista.json())

        # patch (desativa — some da vitrine pública)
        patch = await client.patch(
            f"/api/v1/admin/planos/{plano['id']}",
            headers=admin_headers,
            json={"status": "Inativo"},
        )
        assert patch.status_code == 200
        assert patch.json()["status"] == "Inativo"
        publico = await client.get("/api/v1/planos")
        assert plano["id"] not in [p["id"] for p in publico.json()]

        # delete
        dele = await client.delete(
            f"/api/v1/admin/planos/{plano['id']}", headers=admin_headers
        )
        assert dele.status_code == 204

    async def test_suporte_bloqueado_em_planos(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get("/api/v1/admin/planos", headers=suporte_headers)
        assert resp.status_code == 403
