"""Gate anti-fraude do certificado: 100% instantâneo não basta — é preciso tempo
REAL assistido (>= CERT_MIN_WATCH_RATIO da duração da aula).

Self-contained: cria curso/módulo/aula (com duração) + matrícula próprios e limpa
no fim, sem depender das fixtures compartilhadas do conftest (cujas aulas têm
duracao_segundos=0 e por isso passam trivialmente no gate)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import (
    Aula,
    Certificado,
    Curso,
    Matricula,
    Modulo,
    Progresso,
    StatusMatricula,
    TipoCurso,
)

DURACAO = 600  # 10 min → gate exige >= 0.85 * 600 = 510 s assistidos


@pytest_asyncio.fixture
async def curso_com_duracao(test_aluno: dict):
    """Curso de 1 aula com duracao_segundos=600 + matrícula ativa do test_aluno."""
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)
    aluno_id = uuid.UUID(test_aluno["id"])

    async with Session() as s:
        curso = Curso(
            slug=f"test-fraude-{uuid.uuid4().hex[:6]}",
            titulo="Curso Anti-Fraude",
            tipo=TipoCurso.avulso,
            preco=100.0,
            validade_dias=365,
        )
        s.add(curso)
        await s.flush()
        modulo = Modulo(curso_id=curso.id, titulo="M1", ordem=1)
        s.add(modulo)
        await s.flush()
        aula = Aula(
            modulo_id=modulo.id,
            titulo="Aula com duração",
            duracao_segundos=DURACAO,
            ordem=1,
        )
        s.add(aula)
        await s.flush()
        matricula = Matricula(
            aluno_id=aluno_id,
            curso_id=curso.id,
            status=StatusMatricula.ativo,
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=365),
        )
        s.add(matricula)
        await s.commit()
        ids = {
            "curso_id": curso.id,
            "modulo_id": modulo.id,
            "aula_id": str(aula.id),
            "matricula_id": str(matricula.id),
        }

    yield ids, Session

    async with Session() as s:
        mid = uuid.UUID(ids["matricula_id"])
        await s.execute(delete(Certificado).where(Certificado.matricula_id == mid))
        await s.execute(delete(Progresso).where(Progresso.matricula_id == mid))
        await s.execute(delete(Matricula).where(Matricula.id == mid))
        await s.execute(delete(Aula).where(Aula.id == uuid.UUID(ids["aula_id"])))
        await s.execute(delete(Modulo).where(Modulo.id == ids["modulo_id"]))
        await s.execute(delete(Curso).where(Curso.id == ids["curso_id"]))
        await s.commit()
    await engine.dispose()


class TestGateAntiFraude:
    async def test_100_instantaneo_nao_emite(
        self, client: AsyncClient, auth_headers: dict, curso_com_duracao, monkeypatch
    ):
        """Um único POST 100%/concluída acumula ~0s assistidos → certificado barrado."""
        import app.routers.certificados as cert_router

        async def fake_email(*a, **k):
            return "fake-id"

        monkeypatch.setattr(cert_router, "enviar_email_bruto", fake_email)

        ids, Session = curso_com_duracao

        prog = await client.post(
            "/api/v1/progresso",
            json={"aula_id": ids["aula_id"], "percentual": 100, "concluida": True},
            headers=auth_headers,
        )
        assert prog.status_code == 200

        resp = await client.post(
            f"/api/v1/certificados/{ids['matricula_id']}", headers=auth_headers
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CURSO_NAO_CONCLUIDO"

    async def test_com_tempo_assistido_emite(
        self, client: AsyncClient, auth_headers: dict, curso_com_duracao, monkeypatch
    ):
        """Com tempo real assistido suficiente (>= 85% da duração) → emite (201)."""
        import app.routers.certificados as cert_router

        async def fake_email(*a, **k):
            return "fake-id"

        monkeypatch.setattr(cert_router, "enviar_email_bruto", fake_email)

        ids, Session = curso_com_duracao

        await client.post(
            "/api/v1/progresso",
            json={"aula_id": ids["aula_id"], "percentual": 100, "concluida": True},
            headers=auth_headers,
        )
        # Simula o tempo real assistido (server-side) sem depender do relógio.
        async with Session() as s:
            await s.execute(
                update(Progresso)
                .where(Progresso.matricula_id == uuid.UUID(ids["matricula_id"]))
                .values(segundos_assistidos=int(DURACAO * 0.85))
            )
            await s.commit()

        resp = await client.post(
            f"/api/v1/certificados/{ids['matricula_id']}", headers=auth_headers
        )
        assert resp.status_code == 201
        assert resp.json()["codigo_verificacao"].startswith("RC-")

    async def test_duracao_zero_bloqueia_emissao(
        self, client: AsyncClient, auth_headers: dict, curso_com_duracao, monkeypatch
    ):
        """Aula sem duração cadastrada (duracao_segundos=0) anularia o gate de tempo
        (0>=0). A emissão é recusada (409 DURACAO_NAO_CADASTRADA) até sincronizar."""
        import app.routers.certificados as cert_router

        async def fake_email(*a, **k):
            return "fake-id"

        monkeypatch.setattr(cert_router, "enviar_email_bruto", fake_email)
        ids, Session = curso_com_duracao

        async with Session() as s:  # simula aula não-sincronizada com o Panda
            await s.execute(
                update(Aula)
                .where(Aula.id == uuid.UUID(ids["aula_id"]))
                .values(duracao_segundos=0)
            )
            await s.commit()

        await client.post(
            "/api/v1/progresso",
            json={"aula_id": ids["aula_id"], "percentual": 100, "concluida": True},
            headers=auth_headers,
        )
        resp = await client.post(
            f"/api/v1/certificados/{ids['matricula_id']}", headers=auth_headers
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "DURACAO_NAO_CADASTRADA"
