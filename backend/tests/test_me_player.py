import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models import (
    Aula,
    Curso,
    Matricula,
    Modulo,
    Progresso,
    StatusMatricula,
    TipoCurso,
)


@pytest_asyncio.fixture
async def player_seed(test_aluno):
    """Curso com 2 aulas + matrícula ativa do aluno de teste, e um curso sem
    matrícula (para o caso 403). Limpa tudo ao final."""
    sufixo = uuid.uuid4().hex[:8]
    aluno_uuid = uuid.UUID(test_aluno["id"])
    agora = datetime.now(timezone.utc)
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)

    curso = Curso(
        slug=f"player-{sufixo}",
        titulo="Curso Player Teste",
        tipo=TipoCurso.avulso,
        preco=100.0,
        validade_dias=365,
        horas="3h00",
    )
    curso.modulos = [
        Modulo(
            titulo="Módulo Único",
            ordem=1,
            aulas=[
                Aula(titulo="Aula 1", duracao_segundos=600, ordem=1),
                Aula(titulo="Aula 2", duracao_segundos=720, ordem=2),
            ],
        )
    ]
    curso_sem_mat = Curso(
        slug=f"player-sem-{sufixo}",
        titulo="Curso Sem Matrícula",
        tipo=TipoCurso.avulso,
        preco=100.0,
        validade_dias=365,
    )

    async with Session() as s:
        s.add_all([curso, curso_sem_mat])
        await s.flush()
        matricula = Matricula(
            aluno_id=aluno_uuid,
            curso_id=curso.id,
            status=StatusMatricula.ativo,
            data_expiracao=agora + timedelta(days=30),
        )
        s.add(matricula)
        await s.commit()
        aula_ids = [a.id for m in curso.modulos for a in m.aulas]
        data = {
            "slug": curso.slug,
            "slug_sem_mat": curso_sem_mat.slug,
            "matricula_id": str(matricula.id),
            "aula_ids": [str(a) for a in aula_ids],
            "_curso_ids": [curso.id, curso_sem_mat.id],
            "_matricula_id": matricula.id,
        }

    yield data

    async with Session() as s:
        await s.execute(
            delete(Progresso).where(Progresso.matricula_id == data["_matricula_id"])
        )
        await s.execute(delete(Matricula).where(Matricula.id == data["_matricula_id"]))
        mod_ids = select(Modulo.id).where(Modulo.curso_id.in_(data["_curso_ids"]))
        await s.execute(delete(Aula).where(Aula.modulo_id.in_(mod_ids)))
        await s.execute(delete(Modulo).where(Modulo.curso_id.in_(data["_curso_ids"])))
        await s.execute(delete(Curso).where(Curso.id.in_(data["_curso_ids"])))
        await s.commit()
    await engine.dispose()


class TestPlayerCurso:
    async def test_estrutura_inicial(
        self, client: AsyncClient, auth_headers: dict, player_seed: dict
    ):
        resp = await client.get(
            f"/api/v1/me/cursos/{player_seed['slug']}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["matricula_id"] == player_seed["matricula_id"]
        assert data["horas"] == "3h00"
        assert data["concluido"] is False
        assert data["progresso_percentual"] == 0.0
        assert data["certificado"] is None
        assert len(data["modulos"]) == 1
        assert len(data["modulos"][0]["aulas"]) == 2
        assert data["modulos"][0]["aulas"][0]["duracao_label"] == "10:00"

    async def test_progresso_acumula_e_conclui(
        self, client: AsyncClient, auth_headers: dict, player_seed: dict
    ):
        a1, a2 = player_seed["aula_ids"]

        await client.post(
            "/api/v1/progresso",
            headers=auth_headers,
            json={"aula_id": a1, "percentual": 100, "concluida": True},
        )
        data = (
            await client.get(
                f"/api/v1/me/cursos/{player_seed['slug']}", headers=auth_headers
            )
        ).json()
        assert data["progresso_percentual"] == 50.0
        assert data["concluido"] is False

        await client.post(
            "/api/v1/progresso",
            headers=auth_headers,
            json={"aula_id": a2, "percentual": 100, "concluida": True},
        )
        # `concluido` agora exige tempo REAL assistido (alinhado ao certificado).
        # Acumula segundos suficientes nas duas aulas (>= 0.85 * duração).
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Progresso)
                .where(Progresso.aula_id.in_([uuid.UUID(a1), uuid.UUID(a2)]))
                .values(segundos_assistidos=1000)
            )
            await db.commit()
        data = (
            await client.get(
                f"/api/v1/me/cursos/{player_seed['slug']}", headers=auth_headers
            )
        ).json()
        assert data["progresso_percentual"] == 100.0
        assert data["concluido"] is True

    async def test_sem_token_retorna_401(
        self, client: AsyncClient, player_seed: dict
    ):
        resp = await client.get(f"/api/v1/me/cursos/{player_seed['slug']}")
        assert resp.status_code == 401

    async def test_slug_inexistente_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get(
            "/api/v1/me/cursos/nao-existe-xyz", headers=auth_headers
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CURSO_NAO_ENCONTRADO"

    async def test_curso_sem_matricula_retorna_403(
        self, client: AsyncClient, auth_headers: dict, player_seed: dict
    ):
        resp = await client.get(
            f"/api/v1/me/cursos/{player_seed['slug_sem_mat']}", headers=auth_headers
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ACESSO_NEGADO"
