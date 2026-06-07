import uuid

from httpx import AsyncClient


# ── GET /api/v1/me/matriculas ─────────────────────────────────────────────────
class TestMatriculas:
    async def test_lista_matriculas_retorna_200(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.get("/api/v1/me/matriculas", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    async def test_matricula_ativa_tem_status_ativo(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.get("/api/v1/me/matriculas", headers=auth_headers)
        items = {item["id"]: item for item in resp.json()["items"]}
        ativa = items.get(test_data["matricula_ativa_id"])
        assert ativa is not None
        assert ativa["status"] == "ativo"
        assert ativa["dias_restantes"] > 0

    async def test_matricula_expirada_marcada_como_expirado(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Login dispara checar_vigencia_aluno; matrícula com data passada vira 'expirado'."""
        resp = await client.get("/api/v1/me/matriculas", headers=auth_headers)
        items = {item["id"]: item for item in resp.json()["items"]}
        expirada = items.get(test_data["matricula_expirada_id"])
        assert expirada is not None
        assert expirada["status"] == "expirado"
        assert expirada["dias_restantes"] == 0

    async def test_matriculas_sem_token_retorna_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/me/matriculas")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "NAO_AUTENTICADO"


# ── GET /api/v1/me/dashboard ──────────────────────────────────────────────────
class TestDashboard:
    async def test_dashboard_retorna_estrutura_correta(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/api/v1/me/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ultima_aula" in data
        assert "alertas" in data
        assert "resumo" in data
        resumo = data["resumo"]
        assert "cursos_ativos" in resumo
        assert "aulas_concluidas" in resumo
        assert "certificados" in resumo

    async def test_dashboard_conta_curso_ativo(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.get("/api/v1/me/dashboard", headers=auth_headers)
        assert resp.json()["resumo"]["cursos_ativos"] >= 1

    async def test_dashboard_sem_token_retorna_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/me/dashboard")
        assert resp.status_code == 401


# ── GET /api/v1/aulas/{id} ────────────────────────────────────────────────────
class TestAulas:
    async def test_aula_com_matricula_ativa_retorna_200(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.get(
            f"/api/v1/aulas/{test_data['aula_ativa_id']}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_data["aula_ativa_id"]
        assert "materiais" in data
        prog = data["progresso"]
        assert "concluida" in prog
        assert "percentual" in prog

    async def test_aula_de_curso_expirado_retorna_403(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Matrícula expirada bloqueia o acesso ao conteúdo com 403 MATRICULA_EXPIRADA."""
        resp = await client.get(
            f"/api/v1/aulas/{test_data['aula_expirada_id']}", headers=auth_headers
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "MATRICULA_EXPIRADA"

    async def test_aula_sem_matricula_retorna_403(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Curso sem matrícula alguma retorna 403 ACESSO_NEGADO."""
        resp = await client.get(
            f"/api/v1/aulas/{test_data['aula_sem_mat_id']}", headers=auth_headers
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ACESSO_NEGADO"

    async def test_aula_sem_token_retorna_401(
        self, client: AsyncClient, test_data: dict
    ):
        resp = await client.get(f"/api/v1/aulas/{test_data['aula_ativa_id']}")
        assert resp.status_code == 401

    async def test_aula_inexistente_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get(f"/api/v1/aulas/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "AULA_NAO_ENCONTRADA"
