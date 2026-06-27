import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Aula, Curso, Modulo, StatusCurso, TipoCurso


@pytest_asyncio.fixture
async def cursos_seed():
    """Cria um curso avulso e um premium (com módulos e aulas) e limpa ao final.

    Slugs recebem sufixo aleatório para não colidir com dados reais/seed.
    """
    sufixo = uuid.uuid4().hex[:8]
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    avulso = Curso(
        slug=f"i-motion-{sufixo}",
        titulo="Diagnóstico I-Motion (teste)",
        descricao="Domine o câmbio automatizado I-Motion. " + ("x" * 300),
        tipo=TipoCurso.avulso,
        preco=497.00,
        validade_dias=365,
        thumbnail_url="https://cdn.rodelcar.com.br/cursos/i-motion.jpg",
        destaque=False,
        status=StatusCurso.ativo,
    )
    avulso.modulos = [
        Modulo(
            titulo="Fundamentos",
            ordem=1,
            aulas=[
                Aula(titulo="Aula 1", duracao_segundos=540, ordem=1),
                Aula(titulo="Aula 2", duracao_segundos=600, ordem=2),
            ],
        ),
        Modulo(
            titulo="Diagnóstico",
            ordem=2,
            aulas=[Aula(titulo="Aula 3", duracao_segundos=1280, ordem=1)],
        ),
    ]
    premium = Curso(
        slug=f"premium-{sufixo}",
        titulo="Trilha Premium (teste)",
        descricao="Assinatura premium com a trilha completa.",
        tipo=TipoCurso.premium,
        preco=1490.00,
        validade_dias=365,
        thumbnail_url="https://cdn.rodelcar.com.br/cursos/premium.jpg",
        destaque=True,
        status=StatusCurso.ativo,
    )
    premium.modulos = [
        Modulo(
            titulo="Convencional",
            ordem=1,
            aulas=[Aula(titulo="Aula A", duracao_segundos=820, ordem=1)],
        )
    ]

    async with Session() as session:
        session.add_all([avulso, premium])
        await session.commit()
        ids = {
            "avulso": {"id": avulso.id, "slug": avulso.slug},
            "premium": {"id": premium.id, "slug": premium.slug},
        }

    yield ids

    # Limpeza: aulas → módulos → cursos (sem cascade configurado nos modelos).
    curso_ids = [avulso.id, premium.id]
    async with Session() as session:
        modulo_ids = select(Modulo.id).where(Modulo.curso_id.in_(curso_ids))
        await session.execute(delete(Aula).where(Aula.modulo_id.in_(modulo_ids)))
        await session.execute(delete(Modulo).where(Modulo.curso_id.in_(curso_ids)))
        await session.execute(delete(Curso).where(Curso.id.in_(curso_ids)))
        await session.commit()
    await engine.dispose()


# ── GET /api/v1/cursos ────────────────────────────────────────────────────────
class TestListarCursos:
    async def test_lista_inclui_curso_com_contagens(
        self, client: AsyncClient, cursos_seed: dict
    ):
        resp = await client.get("/api/v1/cursos", params={"size": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)
        assert {"total", "page", "size"} <= data.keys()

        item = next(
            i for i in data["items"] if i["slug"] == cursos_seed["avulso"]["slug"]
        )
        assert item["tipo"] == "avulso"
        assert item["total_modulos"] == 2
        assert item["total_aulas"] == 3
        assert item["preco"] == 497.0

    async def test_descricao_curta_e_truncada(
        self, client: AsyncClient, cursos_seed: dict
    ):
        resp = await client.get("/api/v1/cursos", params={"size": 100})
        item = next(
            i for i in resp.json()["items"]
            if i["slug"] == cursos_seed["avulso"]["slug"]
        )
        # descrição original tem > 160 chars; a curta deve ser truncada com reticências.
        assert len(item["descricao_curta"]) <= 160
        assert item["descricao_curta"].endswith("…")

    async def test_filtro_por_tipo_premium(
        self, client: AsyncClient, cursos_seed: dict
    ):
        resp = await client.get(
            "/api/v1/cursos", params={"tipo": "premium", "size": 100}
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["tipo"] == "premium" for i in items)
        slugs = {i["slug"] for i in items}
        assert cursos_seed["premium"]["slug"] in slugs
        assert cursos_seed["avulso"]["slug"] not in slugs

    async def test_tipo_invalido_retorna_422(self, client: AsyncClient):
        resp = await client.get("/api/v1/cursos", params={"tipo": "inexistente"})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ── GET /api/v1/cursos/{slug} ─────────────────────────────────────────────────
class TestObterCurso:
    async def test_detalhe_retorna_modulos_e_aulas(
        self, client: AsyncClient, cursos_seed: dict
    ):
        slug = cursos_seed["avulso"]["slug"]
        resp = await client.get(f"/api/v1/cursos/{slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == slug
        assert data["tipo"] == "avulso"
        assert "descricao" in data
        assert len(data["modulos"]) == 2

        modulos = sorted(data["modulos"], key=lambda m: m["ordem"])
        assert modulos[0]["titulo"] == "Fundamentos"
        assert modulos[0]["total_aulas"] == 2
        assert modulos[1]["total_aulas"] == 1

    async def test_slug_inexistente_retorna_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/cursos/nao-existe-xyz")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CURSO_NAO_ENCONTRADO"
