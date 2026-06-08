import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models import (
    Aluno,
    Aula,
    Certificado,
    Curso,
    Matricula,
    Modulo,
    Progresso,
    StatusMatricula,
    TipoCurso,
)

TEST_EMAIL = f"test_{uuid.uuid4().hex[:8]}@rodelcar.dev"
TEST_PASSWORD = "TestPass123!"


@pytest_asyncio.fixture(scope="session")
async def test_aluno():
    engine = create_async_engine(settings.DATABASE_URL, connect_args=settings.db_connect_args)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        aluno = Aluno(
            nome="Aluno Teste",
            email=TEST_EMAIL,
            senha_hash=hash_password(TEST_PASSWORD),
        )
        session.add(aluno)
        await session.commit()
        aluno_id = aluno.id

    yield {"id": str(aluno_id), "email": TEST_EMAIL, "password": TEST_PASSWORD}

    async with Session() as session:
        obj = await session.get(Aluno, aluno_id)
        if obj:
            await session.delete(obj)
            await session.commit()
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_data(test_aluno):
    """Cria cursos/módulos/aulas/matrículas para todos os testes de integração."""
    engine = create_async_engine(settings.DATABASE_URL, connect_args=settings.db_connect_args)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    aluno_uuid = uuid.UUID(test_aluno["id"])
    agora = datetime.now(timezone.utc)

    async with Session() as session:
        # ── Curso ativo (para testes de /me, /aulas, /progresso) ──────────────
        curso_ativo = Curso(
            slug=f"test-ativo-{uuid.uuid4().hex[:6]}",
            titulo="Curso Ativo Teste",
            tipo=TipoCurso.avulso,
            preco=100.0,
            validade_dias=365,
        )
        session.add(curso_ativo)
        await session.flush()

        modulo_ativo = Modulo(curso_id=curso_ativo.id, titulo="Módulo 1", ordem=1)
        session.add(modulo_ativo)
        await session.flush()

        aula_ativa = Aula(modulo_id=modulo_ativo.id, titulo="Aula Teste Ativa", ordem=1)
        session.add(aula_ativa)
        await session.flush()

        matricula_ativa = Matricula(
            aluno_id=aluno_uuid,
            curso_id=curso_ativo.id,
            status=StatusMatricula.ativo,
            data_expiracao=agora + timedelta(days=30),
        )
        session.add(matricula_ativa)

        # ── Curso expirado (para testar MATRICULA_EXPIRADA) ───────────────────
        curso_expirado = Curso(
            slug=f"test-exp-{uuid.uuid4().hex[:6]}",
            titulo="Curso Expirado Teste",
            tipo=TipoCurso.avulso,
            preco=100.0,
            validade_dias=30,
        )
        session.add(curso_expirado)
        await session.flush()

        modulo_expirado = Modulo(curso_id=curso_expirado.id, titulo="Módulo Exp", ordem=1)
        session.add(modulo_expirado)
        await session.flush()

        aula_expirada = Aula(
            modulo_id=modulo_expirado.id, titulo="Aula Expirada", ordem=1
        )
        session.add(aula_expirada)
        await session.flush()

        matricula_expirada = Matricula(
            aluno_id=aluno_uuid,
            curso_id=curso_expirado.id,
            status=StatusMatricula.ativo,
            data_expiracao=agora - timedelta(days=5),
        )
        session.add(matricula_expirada)

        # ── Curso sem matrícula (para testar ACESSO_NEGADO) ───────────────────
        curso_sem_mat = Curso(
            slug=f"test-sem-{uuid.uuid4().hex[:6]}",
            titulo="Curso Sem Matrícula",
            tipo=TipoCurso.avulso,
            preco=100.0,
            validade_dias=365,
        )
        session.add(curso_sem_mat)
        await session.flush()

        modulo_sem_mat = Modulo(curso_id=curso_sem_mat.id, titulo="Módulo SM", ordem=1)
        session.add(modulo_sem_mat)
        await session.flush()

        aula_sem_mat = Aula(
            modulo_id=modulo_sem_mat.id, titulo="Aula Sem Matrícula", ordem=1
        )
        session.add(aula_sem_mat)
        await session.flush()

        # ── Curso dedicado para testes de certificado (1 aula) ────────────────
        curso_cert = Curso(
            slug=f"test-cert-{uuid.uuid4().hex[:6]}",
            titulo="Curso Certificado Teste",
            tipo=TipoCurso.avulso,
            preco=100.0,
            validade_dias=365,
        )
        session.add(curso_cert)
        await session.flush()

        modulo_cert = Modulo(curso_id=curso_cert.id, titulo="Módulo Cert", ordem=1)
        session.add(modulo_cert)
        await session.flush()

        aula_cert = Aula(modulo_id=modulo_cert.id, titulo="Aula Cert", ordem=1)
        session.add(aula_cert)
        await session.flush()

        matricula_cert = Matricula(
            aluno_id=aluno_uuid,
            curso_id=curso_cert.id,
            status=StatusMatricula.ativo,
            data_expiracao=agora + timedelta(days=30),
        )
        session.add(matricula_cert)

        await session.commit()

        data = {
            # Curso ativo
            "curso_ativo_id": str(curso_ativo.id),
            "modulo_ativo_id": str(modulo_ativo.id),
            "aula_ativa_id": str(aula_ativa.id),
            "matricula_ativa_id": str(matricula_ativa.id),
            # Curso expirado
            "curso_expirado_id": str(curso_expirado.id),
            "modulo_expirado_id": str(modulo_expirado.id),
            "aula_expirada_id": str(aula_expirada.id),
            "matricula_expirada_id": str(matricula_expirada.id),
            # Curso sem matrícula
            "curso_sem_mat_id": str(curso_sem_mat.id),
            "modulo_sem_mat_id": str(modulo_sem_mat.id),
            "aula_sem_mat_id": str(aula_sem_mat.id),
            # Curso para certificado
            "curso_cert_id": str(curso_cert.id),
            "modulo_cert_id": str(modulo_cert.id),
            "aula_cert_id": str(aula_cert.id),
            "matricula_cert_id": str(matricula_cert.id),
        }

    yield data

    # Cleanup em ordem reversa de FK:
    # Certificado → Progresso → Matricula → Aula → Modulo → Curso
    async with Session() as session:
        mat_ids = [
            uuid.UUID(data["matricula_ativa_id"]),
            uuid.UUID(data["matricula_expirada_id"]),
            uuid.UUID(data["matricula_cert_id"]),
        ]
        aula_ids = [
            uuid.UUID(data["aula_ativa_id"]),
            uuid.UUID(data["aula_expirada_id"]),
            uuid.UUID(data["aula_sem_mat_id"]),
            uuid.UUID(data["aula_cert_id"]),
        ]
        modulo_ids = [
            uuid.UUID(data["modulo_ativo_id"]),
            uuid.UUID(data["modulo_expirado_id"]),
            uuid.UUID(data["modulo_sem_mat_id"]),
            uuid.UUID(data["modulo_cert_id"]),
        ]
        curso_ids = [
            uuid.UUID(data["curso_ativo_id"]),
            uuid.UUID(data["curso_expirado_id"]),
            uuid.UUID(data["curso_sem_mat_id"]),
            uuid.UUID(data["curso_cert_id"]),
        ]
        await session.execute(
            delete(Certificado).where(Certificado.matricula_id.in_(mat_ids))
        )
        await session.execute(
            delete(Progresso).where(Progresso.matricula_id.in_(mat_ids))
        )
        await session.execute(delete(Matricula).where(Matricula.id.in_(mat_ids)))
        await session.execute(delete(Aula).where(Aula.id.in_(aula_ids)))
        await session.execute(delete(Modulo).where(Modulo.id.in_(modulo_ids)))
        await session.execute(delete(Curso).where(Curso.id.in_(curso_ids)))
        await session.commit()

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
def _reset_rate_limiter():
    """Zera o contador do rate limiter entre testes.

    O storage do slowapi é in-memory e persiste na sessão; sem o reset, o teto
    estrito de auth (5/min) vaza de um teste para o outro e gera 429 espúrio.
    """
    from app.core.ratelimit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_aluno: dict) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_aluno["email"], "senha": test_aluno["password"]},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
