"""Testes dos ajustes do painel admin:
- Curso ativar/inativar + propagação na vitrine pública.
- Aluno: validação de telefone, bloqueio (login + sessão), reset de senha por link.
- Reembolso: listagem de matrículas com filtros.
- Métricas diárias da visão geral.
"""
import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    Admin,
    Aluno,
    Aula,
    Curso,
    Modulo,
    PapelAdmin,
    PasswordReset,
    StatusCurso,
    TipoCurso,
)


def _session():
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient):
    email = f"admin_aj_{uuid.uuid4().hex[:8]}@rodelcar.dev"
    senha = "AdminAj123!"
    engine, Session = _session()
    async with Session() as s:
        admin = Admin(
            nome="Admin Ajustes",
            email=email,
            senha_hash=hash_password(senha),
            papel=PapelAdmin.administrador,
            ativo=True,
        )
        s.add(admin)
        await s.commit()
        admin_id = admin.id
    resp = await client.post(
        "/api/v1/admin/auth/login", json={"email": email, "senha": senha}
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    yield headers
    async with Session() as s:
        obj = await s.get(Admin, admin_id)
        if obj:
            await s.delete(obj)
            await s.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def curso_temp():
    """Cria um curso (ativo, com módulo+aula) direto no banco e o remove no fim.

    O conteúdo é necessário porque ativar um curso pelo painel agora exige ao
    menos uma aula (CURSO_SEM_CONTEUDO); o teste de reativação depende disso.
    """
    engine, Session = _session()
    slug = f"aj-{uuid.uuid4().hex[:8]}"
    async with Session() as s:
        curso = Curso(
            slug=slug,
            titulo="Curso Ajustes Teste",
            tipo=TipoCurso.avulso,
            preco=100.0,
            validade_dias=365,
            status=StatusCurso.ativo,
        )
        s.add(curso)
        await s.flush()
        modulo = Modulo(curso_id=curso.id, titulo="Módulo Ajustes", ordem=1)
        s.add(modulo)
        await s.flush()
        aula = Aula(modulo_id=modulo.id, titulo="Aula Ajustes", ordem=1)
        s.add(aula)
        await s.commit()
        curso_id = curso.id
        modulo_id = modulo.id
        aula_id = aula.id
    yield {"id": str(curso_id), "slug": slug}
    async with Session() as s:
        await s.execute(delete(Aula).where(Aula.id == aula_id))
        await s.execute(delete(Modulo).where(Modulo.id == modulo_id))
        obj = await s.get(Curso, curso_id)
        if obj:
            await s.delete(obj)
            await s.commit()
    await engine.dispose()


async def _delete_aluno(aluno_id: str):
    engine, Session = _session()
    async with Session() as s:
        await s.execute(
            delete(PasswordReset).where(PasswordReset.aluno_id == uuid.UUID(aluno_id))
        )
        obj = await s.get(Aluno, uuid.UUID(aluno_id))
        if obj:
            await s.delete(obj)
        await s.commit()
    await engine.dispose()


# ── Curso ativar/inativar + propagação ────────────────────────────────────────
class TestCursoAtivo:
    async def test_inativar_some_da_vitrine_e_volta(
        self, client: AsyncClient, admin_headers: dict, curso_temp: dict
    ):
        slug = curso_temp["slug"]
        cid = curso_temp["id"]

        # Ativo: aparece na vitrine e na página de venda.
        lista = await client.get("/api/v1/cursos?size=100")
        assert any(c["slug"] == slug for c in lista.json()["items"])
        assert (await client.get(f"/api/v1/cursos/{slug}")).status_code == 200

        # Inativa pelo painel (reusa o PATCH genérico do curso).
        r = await client.patch(
            f"/api/v1/admin/cursos/{cid}",
            headers=admin_headers,
            json={"status": "inativo"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "inativo"

        # Sumiu da vitrine pública e o slug dá 404.
        lista = await client.get("/api/v1/cursos?size=100")
        assert not any(c["slug"] == slug for c in lista.json()["items"])
        assert (await client.get(f"/api/v1/cursos/{slug}")).status_code == 404

        # Reativa → volta (o curso tem conteúdo, então a ativação é permitida).
        await client.patch(
            f"/api/v1/admin/cursos/{cid}", headers=admin_headers, json={"status": "ativo"}
        )
        assert (await client.get(f"/api/v1/cursos/{slug}")).status_code == 200


# ── Aluno: telefone, bloqueio e reset de senha ────────────────────────────────
class TestAlunoGestao:
    async def test_telefone_invalido_422(
        self, client: AsyncClient, admin_headers: dict
    ):
        r = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={
                "nome": "Fulano",
                "email": f"tel_{uuid.uuid4().hex[:6]}@rodelcar.dev",
                "senha": "SenhaForte123",
                "telefone": "123",
            },
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_bloqueio_barra_login_e_libera(
        self, client: AsyncClient, admin_headers: dict
    ):
        email = f"bloq_{uuid.uuid4().hex[:6]}@rodelcar.dev"
        senha = "SenhaForte123"
        criado = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "Bloqueável", "email": email, "senha": senha},
        )
        assert criado.status_code == 201
        aluno_id = criado.json()["id"]
        try:
            # Login funciona antes do bloqueio.
            assert (
                await client.post(
                    "/api/v1/auth/login", json={"email": email, "senha": senha}
                )
            ).status_code == 200

            # Bloqueia → login 403 ALUNO_BLOQUEADO.
            b = await client.post(
                f"/api/v1/admin/alunos/{aluno_id}/bloquear",
                headers=admin_headers,
                json={"bloqueado": True},
            )
            assert b.status_code == 200
            assert b.json()["status"] == "Bloqueado"
            neg = await client.post(
                "/api/v1/auth/login", json={"email": email, "senha": senha}
            )
            assert neg.status_code == 403
            assert neg.json()["error"]["code"] == "ALUNO_BLOQUEADO"

            # Desbloqueia → login volta a funcionar.
            await client.post(
                f"/api/v1/admin/alunos/{aluno_id}/bloquear",
                headers=admin_headers,
                json={"bloqueado": False},
            )
            assert (
                await client.post(
                    "/api/v1/auth/login", json={"email": email, "senha": senha}
                )
            ).status_code == 200
        finally:
            await _delete_aluno(aluno_id)

    async def test_bloqueio_barra_refresh_token(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Refresh token pré-existente não renova sessão após o bloqueio."""
        email = f"refbloq_{uuid.uuid4().hex[:6]}@rodelcar.dev"
        senha = "SenhaForte123"
        criado = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "Refresh Bloq", "email": email, "senha": senha},
        )
        aluno_id = criado.json()["id"]
        try:
            login = await client.post(
                "/api/v1/auth/login", json={"email": email, "senha": senha}
            )
            refresh_token = login.json()["refresh_token"]

            await client.post(
                f"/api/v1/admin/alunos/{aluno_id}/bloquear",
                headers=admin_headers,
                json={"bloqueado": True},
            )
            r = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
            )
            assert r.status_code == 403
            assert r.json()["error"]["code"] == "ALUNO_BLOQUEADO"
        finally:
            await _delete_aluno(aluno_id)

    async def test_recuperar_senha_gerar_novo_invalida_anterior(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Gerar um novo link de reset invalida o anterior (1 token vivo)."""
        email = f"reset2_{uuid.uuid4().hex[:6]}@rodelcar.dev"
        criado = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "Dois Links", "email": email, "senha": "SenhaForte123"},
        )
        aluno_id = criado.json()["id"]
        try:
            t1 = (
                await client.post(
                    f"/api/v1/admin/alunos/{aluno_id}/recuperar-senha",
                    headers=admin_headers,
                )
            ).json()["token"]
            t2 = (
                await client.post(
                    f"/api/v1/admin/alunos/{aluno_id}/recuperar-senha",
                    headers=admin_headers,
                )
            ).json()["token"]

            # O 1º token (anterior) não vale mais.
            r1 = await client.post(
                "/api/v1/auth/recuperar-senha/confirmar",
                json={"token": t1, "nova_senha": "NovaSenha456"},
            )
            assert r1.status_code == 400
            # O 2º (mais recente) funciona.
            r2 = await client.post(
                "/api/v1/auth/recuperar-senha/confirmar",
                json={"token": t2, "nova_senha": "NovaSenha456"},
            )
            assert r2.status_code == 204
        finally:
            await _delete_aluno(aluno_id)

    async def test_recuperar_senha_link_redefine_e_e_single_use(
        self, client: AsyncClient, admin_headers: dict
    ):
        email = f"reset_{uuid.uuid4().hex[:6]}@rodelcar.dev"
        senha = "SenhaForte123"
        criado = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "Esquecido", "email": email, "senha": senha},
        )
        aluno_id = criado.json()["id"]
        try:
            r = await client.post(
                f"/api/v1/admin/alunos/{aluno_id}/recuperar-senha",
                headers=admin_headers,
            )
            assert r.status_code == 200
            token = r.json()["token"]
            assert token

            nova = "NovaSenha456"
            ok = await client.post(
                "/api/v1/auth/recuperar-senha/confirmar",
                json={"token": token, "nova_senha": nova},
            )
            assert ok.status_code == 204

            # Senha antiga não vale mais; a nova funciona.
            assert (
                await client.post(
                    "/api/v1/auth/login", json={"email": email, "senha": senha}
                )
            ).status_code == 401
            assert (
                await client.post(
                    "/api/v1/auth/login", json={"email": email, "senha": nova}
                )
            ).status_code == 200

            # Token é single-use → 2ª tentativa falha.
            reuso = await client.post(
                "/api/v1/auth/recuperar-senha/confirmar",
                json={"token": token, "nova_senha": "OutraSenha789"},
            )
            assert reuso.status_code == 400
            assert reuso.json()["error"]["code"] == "TOKEN_INVALIDO"
        finally:
            await _delete_aluno(aluno_id)

    async def test_recuperar_senha_dispara_email_com_link(
        self, client: AsyncClient, admin_headers: dict, monkeypatch
    ):
        """Ao gerar a recuperação, o link vai automático para o e-mail do aluno."""
        import app.routers.admin as admin_router

        enviados: list[tuple[str, str, str]] = []

        async def fake_email(para, assunto, corpo, *, log_ref="?"):
            enviados.append((para, assunto, corpo))
            return "fake-id"

        monkeypatch.setattr(admin_router, "enviar_email_bruto", fake_email)

        email = f"resetmail_{uuid.uuid4().hex[:6]}@rodelcar.dev"
        criado = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "Maria Silva", "email": email, "senha": "SenhaForte123"},
        )
        aluno_id = criado.json()["id"]
        try:
            r = await client.post(
                f"/api/v1/admin/alunos/{aluno_id}/recuperar-senha",
                headers=admin_headers,
            )
            assert r.status_code == 200
            token = r.json()["token"]

            # E-mail disparado UMA vez, para o aluno, com o link contendo o token.
            assert len(enviados) == 1
            para, _assunto, corpo = enviados[0]
            assert para == email
            assert f"/recuperar-senha?token={token}" in corpo
        finally:
            await _delete_aluno(aluno_id)


# ── Reembolso: listagem de matrículas + métricas ──────────────────────────────
class TestReembolsoEMetricas:
    async def test_listar_matriculas_default_ativo(
        self, client: AsyncClient, admin_headers: dict, test_data: dict
    ):
        r = await client.get(
            "/api/v1/admin/reembolsos/matriculas", headers=admin_headers
        )
        assert r.status_code == 200
        linhas = r.json()
        assert isinstance(linhas, list)
        # A matrícula ativa do test_data deve aparecer (default = ativos).
        assert any(
            m["matricula_id"] == test_data["matricula_ativa_id"] for m in linhas
        )

    async def test_metricas_diario_serie_continua(
        self, client: AsyncClient, admin_headers: dict
    ):
        r = await client.get(
            "/api/v1/admin/metricas/diario?dias=7", headers=admin_headers
        )
        assert r.status_code == 200
        pontos = r.json()
        assert len(pontos) == 7
        for p in pontos:
            assert {"dia", "acessos", "aulas_assistidas", "compras"} <= set(p.keys())

    async def test_metricas_exige_admin(self, client: AsyncClient):
        r = await client.get("/api/v1/admin/metricas/diario")
        assert r.status_code == 401
