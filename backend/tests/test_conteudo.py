import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Depoimento, Faq, TurmaMidia, Video


@pytest_asyncio.fixture
async def conteudo_seed():
    """Cria conteúdo público com 1 item visível + 1 oculto por entidade e limpa."""
    sufixo = uuid.uuid4().hex[:8]
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)

    dep_ok = Depoimento(
        nome=f"Aprovado {sufixo}", texto="Depoimento aprovado", estrelas=5,
        status="Aprovado", ordem=0,
    )
    dep_pend = Depoimento(
        nome=f"Pendente {sufixo}", texto="Aguardando", estrelas=4,
        status="Pendente", ordem=0,
    )
    vid_on = Video(
        titulo=f"Video On {sufixo}", duracao="10:00", views="1 mil",
        youtube_url="https://youtu.be/x", status="Ativo", ordem=0,
    )
    vid_off = Video(titulo=f"Video Off {sufixo}", status="Inativo", ordem=0)
    faq_on = Faq(
        pergunta=f"Pergunta On {sufixo}?", resposta="Resposta", status="Ativo", ordem=0
    )
    faq_off = Faq(
        pergunta=f"Pergunta Off {sufixo}?", resposta="Resposta", status="Inativo", ordem=0
    )
    tm_on = TurmaMidia(
        url="https://example.com/t1.jpg", alt=f"Turma On {sufixo}",
        destaque=True, status="Ativo", ordem=0,
    )
    tm_off = TurmaMidia(
        url="https://example.com/t2.jpg", alt=f"Turma Off {sufixo}",
        status="Inativo", ordem=0,
    )

    async with Session() as s:
        s.add_all([dep_ok, dep_pend, vid_on, vid_off, faq_on, faq_off, tm_on, tm_off])
        await s.commit()
        data = {
            "dep_ok_nome": dep_ok.nome,
            "dep_pend_nome": dep_pend.nome,
            "vid_on_titulo": vid_on.titulo,
            "vid_off_titulo": vid_off.titulo,
            "faq_on_pergunta": faq_on.pergunta,
            "faq_off_pergunta": faq_off.pergunta,
            "tm_on_alt": tm_on.alt,
            "tm_off_alt": tm_off.alt,
            "_dep_ids": [dep_ok.id, dep_pend.id],
            "_vid_ids": [vid_on.id, vid_off.id],
            "_faq_ids": [faq_on.id, faq_off.id],
            "_tm_ids": [tm_on.id, tm_off.id],
        }

    yield data

    async with Session() as s:
        await s.execute(delete(Depoimento).where(Depoimento.id.in_(data["_dep_ids"])))
        await s.execute(delete(Video).where(Video.id.in_(data["_vid_ids"])))
        await s.execute(delete(Faq).where(Faq.id.in_(data["_faq_ids"])))
        await s.execute(delete(TurmaMidia).where(TurmaMidia.id.in_(data["_tm_ids"])))
        await s.commit()
    await engine.dispose()


class TestDepoimentosPublico:
    async def test_lista_apenas_aprovados(self, client: AsyncClient, conteudo_seed: dict):
        resp = await client.get("/api/v1/depoimentos")
        assert resp.status_code == 200
        nomes = {d["nome"] for d in resp.json()}
        assert conteudo_seed["dep_ok_nome"] in nomes
        assert conteudo_seed["dep_pend_nome"] not in nomes

    async def test_nao_expoe_status_nem_ordem(self, client: AsyncClient, conteudo_seed: dict):
        item = next(
            d for d in (await client.get("/api/v1/depoimentos")).json()
            if d["nome"] == conteudo_seed["dep_ok_nome"]
        )
        assert "status" not in item
        assert "ordem" not in item
        assert {"nome", "papel", "estrelas", "texto"} <= item.keys()


class TestVideosPublico:
    async def test_lista_apenas_ativos(self, client: AsyncClient, conteudo_seed: dict):
        resp = await client.get("/api/v1/videos")
        assert resp.status_code == 200
        titulos = {v["titulo"] for v in resp.json()}
        assert conteudo_seed["vid_on_titulo"] in titulos
        assert conteudo_seed["vid_off_titulo"] not in titulos

    async def test_nao_expoe_status(self, client: AsyncClient, conteudo_seed: dict):
        item = next(
            v for v in (await client.get("/api/v1/videos")).json()
            if v["titulo"] == conteudo_seed["vid_on_titulo"]
        )
        assert "status" not in item
        assert item["youtube_url"] == "https://youtu.be/x"


class TestFaqPublico:
    async def test_lista_apenas_ativos(self, client: AsyncClient, conteudo_seed: dict):
        resp = await client.get("/api/v1/faq")
        assert resp.status_code == 200
        perguntas = {f["pergunta"] for f in resp.json()}
        assert conteudo_seed["faq_on_pergunta"] in perguntas
        assert conteudo_seed["faq_off_pergunta"] not in perguntas


class TestTurmasMidiaPublico:
    async def test_lista_apenas_ativas(self, client: AsyncClient, conteudo_seed: dict):
        resp = await client.get("/api/v1/turmas-midia")
        assert resp.status_code == 200
        alts = {m["alt"] for m in resp.json()}
        assert conteudo_seed["tm_on_alt"] in alts
        assert conteudo_seed["tm_off_alt"] not in alts

    async def test_nao_expoe_status_nem_ordem(self, client: AsyncClient, conteudo_seed: dict):
        item = next(
            m for m in (await client.get("/api/v1/turmas-midia")).json()
            if m["alt"] == conteudo_seed["tm_on_alt"]
        )
        assert "status" not in item
        assert "ordem" not in item
        assert item["destaque"] is True
        assert {"url", "alt", "destaque"} <= item.keys()
