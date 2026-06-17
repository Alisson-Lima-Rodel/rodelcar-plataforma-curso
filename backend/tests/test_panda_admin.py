"""Endpoints admin de upload/sync de vídeo (Panda), com o cliente Panda mockado.

Valida a lógica do backend (gating por chave, gravação do video_id, preenchimento
da duração) sem depender de credenciais reais nem de rede."""
import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.routers.admin as admin_mod
from app.core.config import settings
from app.models import Aula, Curso, Modulo, TipoCurso


@pytest_asyncio.fixture
async def aula_admin():
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        curso = Curso(
            slug=f"test-panda-{uuid.uuid4().hex[:6]}",
            titulo="Curso Panda",
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
            titulo="Aula Panda",
            panda_video_id="vid-existente",
            duracao_segundos=0,
            ordem=1,
        )
        s.add(aula)
        await s.commit()
        ids = {"curso_id": curso.id, "modulo_id": modulo.id, "aula_id": str(aula.id)}

    yield ids, Session

    async with Session() as s:
        await s.execute(delete(Aula).where(Aula.id == uuid.UUID(ids["aula_id"])))
        await s.execute(delete(Modulo).where(Modulo.id == ids["modulo_id"]))
        await s.execute(delete(Curso).where(Curso.id == ids["curso_id"]))
        await s.commit()
    await engine.dispose()


class TestUploadPanda:
    async def test_sem_chave_retorna_503(
        self, client: AsyncClient, admin_token: dict, aula_admin, monkeypatch
    ):
        monkeypatch.setattr(admin_mod.settings, "PANDA_API_KEY", "")
        ids, _ = aula_admin
        resp = await client.post(
            f"/api/v1/admin/aulas/{ids['aula_id']}/upload-url",
            json={"filename": "aula.mp4", "size": 1024},
            headers=admin_token,
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "PANDA_INDISPONIVEL"

    async def test_gera_url_e_salva_video_id(
        self, client: AsyncClient, admin_token: dict, aula_admin, monkeypatch
    ):
        monkeypatch.setattr(admin_mod.settings, "PANDA_API_KEY", "testkey")

        async def fake_criar_upload(*, filename, size, video_id=None, folder_id=None):
            assert filename == "aula.mp4" and size == 2048
            return {
                "video_id": "vid-novo-123",
                "upload_url": "https://uploader-us01.pandavideo.com.br/files/abc",
            }

        monkeypatch.setattr(admin_mod.panda, "criar_upload", fake_criar_upload)

        ids, Session = aula_admin
        resp = await client.post(
            f"/api/v1/admin/aulas/{ids['aula_id']}/upload-url",
            json={"filename": "aula.mp4", "size": 2048},
            headers=admin_token,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "vid-novo-123"
        assert data["upload_url"].startswith("https://uploader-")

        async with Session() as s:
            a = await s.get(Aula, uuid.UUID(ids["aula_id"]))
            assert a.panda_video_id == "vid-novo-123"

    async def test_sync_preenche_duracao(
        self, client: AsyncClient, admin_token: dict, aula_admin, monkeypatch
    ):
        monkeypatch.setattr(admin_mod.settings, "PANDA_API_KEY", "testkey")

        async def fake_obter_video(video_id):
            return {
                "length": 600,
                "status": "CONVERTED",
                "thumbnail": "https://b.tv/thumb.jpg",
            }

        monkeypatch.setattr(admin_mod.panda, "obter_video", fake_obter_video)

        ids, Session = aula_admin
        resp = await client.post(
            f"/api/v1/admin/aulas/{ids['aula_id']}/sync-panda",
            headers=admin_token,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["duracao_segundos"] == 600
        assert data["status"] == "CONVERTED"
        assert data["thumbnail"] == "https://b.tv/thumb.jpg"

        async with Session() as s:
            a = await s.get(Aula, uuid.UUID(ids["aula_id"]))
            assert a.duracao_segundos == 600


class TestDrmToken:
    def test_sem_drm_retorna_none(self, monkeypatch):
        from app.core import panda

        monkeypatch.setattr(panda.settings, "PANDA_DRM_ENABLED", False)
        assert panda.assinar_drm_token() is None

    def test_com_drm_assina_jwt(self, monkeypatch):
        import jwt as jwtlib

        from app.core import panda

        monkeypatch.setattr(panda.settings, "PANDA_DRM_ENABLED", True)
        monkeypatch.setattr(panda.settings, "PANDA_DRM_GROUP_ID", "grp-1")
        monkeypatch.setattr(panda.settings, "PANDA_DRM_SECRET", "s3cr3t-xyz")
        tok = panda.assinar_drm_token(ttl=60)
        assert tok
        dec = jwtlib.decode(tok, "s3cr3t-xyz", algorithms=["HS256"])
        assert dec["drm_group_id"] == "grp-1"
        assert "exp" in dec

    async def test_aula_inclui_token_quando_drm_ligado(
        self, client: AsyncClient, auth_headers: dict, test_data: dict, monkeypatch
    ):
        from app.core import panda

        monkeypatch.setattr(panda.settings, "PANDA_DRM_ENABLED", True)
        monkeypatch.setattr(panda.settings, "PANDA_DRM_GROUP_ID", "grp-1")
        monkeypatch.setattr(panda.settings, "PANDA_DRM_SECRET", "s3cr3t-xyz")
        r = await client.get(
            f"/api/v1/aulas/{test_data['aula_ativa_id']}", headers=auth_headers
        )
        assert r.status_code == 200
        d = r.json()
        assert d["player_token"]
        assert d["drm_group_id"] == "grp-1"

    async def test_aula_sem_token_quando_drm_desligado(
        self, client: AsyncClient, auth_headers: dict, test_data: dict, monkeypatch
    ):
        from app.core import panda

        monkeypatch.setattr(panda.settings, "PANDA_DRM_ENABLED", False)
        r = await client.get(
            f"/api/v1/aulas/{test_data['aula_ativa_id']}", headers=auth_headers
        )
        assert r.status_code == 200
        assert r.json()["player_token"] is None


class TestBiblioteca:
    def test_itens_biblioteca_normaliza(self):
        from app.core import panda

        itens = panda.itens_biblioteca(
            {
                "videos": [
                    {
                        "id": "v1",
                        "title": "Intro",
                        "length": 90.7,
                        "thumbnail": "https://b.tv/1.jpg",
                        "status": "CONVERTED",
                    },
                    {"video_id": "v2", "title": "Sem capa"},
                    {"title": "Sem id — descartado"},
                ]
            }
        )
        assert [i["id"] for i in itens] == ["v1", "v2"]
        assert itens[0]["duracao_segundos"] == 90
        assert itens[0]["titulo"] == "Intro"
        assert itens[1]["thumbnail"] is None

    def test_itens_pastas_normaliza(self):
        from app.core import panda

        pastas = panda.itens_pastas({"folders": [{"id": "f1", "name": "Curso A"}, {}]})
        assert pastas == [{"id": "f1", "nome": "Curso A"}]

    async def test_videos_sem_chave_retorna_503(
        self, client: AsyncClient, admin_token: dict, monkeypatch
    ):
        monkeypatch.setattr(admin_mod.settings, "PANDA_API_KEY", "")
        resp = await client.get("/api/v1/admin/panda/videos", headers=admin_token)
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "PANDA_INDISPONIVEL"

    async def test_lista_videos_repassa_filtros(
        self, client: AsyncClient, admin_token: dict, monkeypatch
    ):
        monkeypatch.setattr(admin_mod.settings, "PANDA_API_KEY", "testkey")
        capturado = {}

        async def fake_listar_videos(*, page, limit, title, folder_id):
            capturado.update(page=page, limit=limit, title=title, folder_id=folder_id)
            return {
                "videos": [
                    {"id": "v1", "title": "Aula 1", "length": 120, "status": "CONVERTED"}
                ]
            }

        monkeypatch.setattr(admin_mod.panda, "listar_videos", fake_listar_videos)

        resp = await client.get(
            "/api/v1/admin/panda/videos?title=aula&folder_id=f1&page=2&limit=10",
            headers=admin_token,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2 and data["limit"] == 10
        assert data["itens"][0] == {
            "id": "v1",
            "titulo": "Aula 1",
            "duracao_segundos": 120,
            "thumbnail": None,
            "status": "CONVERTED",
        }
        assert capturado == {"page": 2, "limit": 10, "title": "aula", "folder_id": "f1"}

    async def test_lista_pastas(
        self, client: AsyncClient, admin_token: dict, monkeypatch
    ):
        monkeypatch.setattr(admin_mod.settings, "PANDA_API_KEY", "testkey")

        async def fake_listar_pastas(*, parent_folder_id=None):
            return {"folders": [{"id": "f1", "name": "Mecânica"}]}

        monkeypatch.setattr(admin_mod.panda, "listar_pastas", fake_listar_pastas)

        resp = await client.get("/api/v1/admin/panda/pastas", headers=admin_token)
        assert resp.status_code == 200
        assert resp.json()["itens"] == [{"id": "f1", "nome": "Mecânica"}]


class TestRetencao:
    def test_pontos_ordenados(self):
        from app.core import panda

        pts = panda.pontos_retencao(
            {"retention": {"0": 100, "10": 80, "5": 90, "x": 1}}
        )
        assert pts == [
            {"segundo": 0, "percentual": 100.0},
            {"segundo": 5, "percentual": 90.0},
            {"segundo": 10, "percentual": 80.0},
        ]

    async def test_endpoint_retorna_curva(
        self, client: AsyncClient, admin_token: dict, aula_admin, monkeypatch
    ):
        monkeypatch.setattr(admin_mod.settings, "PANDA_API_KEY", "testkey")

        async def fake_retencao(video_id, *, start_date=None, end_date=None):
            return {
                "retention": {"0": 100, "5": 88, "10": 70},
                "video": {"duration": 120},
            }

        monkeypatch.setattr(admin_mod.panda, "retencao", fake_retencao)

        ids, _ = aula_admin
        resp = await client.get(
            f"/api/v1/admin/aulas/{ids['aula_id']}/retencao", headers=admin_token
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["duracao_segundos"] == 120
        assert data["pontos"][0] == {"segundo": 0, "percentual": 100.0}
        assert [p["segundo"] for p in data["pontos"]] == [0, 5, 10]
