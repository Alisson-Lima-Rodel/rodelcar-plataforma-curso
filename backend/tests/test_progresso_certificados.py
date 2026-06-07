import uuid

from httpx import AsyncClient


# ── POST /api/v1/progresso ────────────────────────────────────────────────────
class TestProgresso:
    async def test_salva_progresso_retorna_200(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={
                "aula_id": test_data["aula_ativa_id"],
                "percentual": 60,
                "concluida": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["aula_id"] == test_data["aula_ativa_id"]
        assert data["percentual"] == 60
        assert data["concluida"] is False
        assert "curso_percentual" in data
        # Curso tem 1 aula com 60 % → curso_percentual == 60.0
        assert data["curso_percentual"] == 60.0

    async def test_upsert_atualiza_percentual(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Segunda chamada com mesma aula deve fazer upsert, não criar duplicata."""
        await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 30, "concluida": False},
            headers=auth_headers,
        )
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 85, "concluida": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["percentual"] == 85

    async def test_curso_percentual_100_quando_aula_concluida(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Marcar aula como concluída (100 %) → curso_percentual == 100.0."""
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 100, "concluida": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["curso_percentual"] == 100.0

    async def test_progresso_sem_matricula_retorna_403(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={
                "aula_id": test_data["aula_sem_mat_id"],
                "percentual": 50,
                "concluida": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ACESSO_NEGADO"

    async def test_progresso_aula_inexistente_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": str(uuid.uuid4()), "percentual": 50, "concluida": False},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_progresso_sem_token_retorna_401(
        self, client: AsyncClient, test_data: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 50, "concluida": False},
        )
        assert resp.status_code == 401

    async def test_progresso_percentual_invalido_retorna_422(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 150, "concluida": False},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ── POST + GET /api/v1/certificados ──────────────────────────────────────────
class TestCertificados:
    async def test_sem_conclusao_retorna_409(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Sem progresso → não pode emitir certificado (409 CURSO_NAO_CONCLUIDO)."""
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CURSO_NAO_CONCLUIDO"

    async def test_fluxo_completo_emitir_e_verificar(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Conclui a única aula → emite certificado → verifica código publicamente."""
        # 1. Marca aula_cert como 100 % concluída
        prog_resp = await client.post(
            "/api/v1/progresso",
            json={
                "aula_id": test_data["aula_cert_id"],
                "percentual": 100,
                "concluida": True,
            },
            headers=auth_headers,
        )
        assert prog_resp.status_code == 200
        assert prog_resp.json()["curso_percentual"] == 100.0

        # 2. Emite certificado
        cert_resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}",
            headers=auth_headers,
        )
        assert cert_resp.status_code == 201
        cert = cert_resp.json()
        assert "id" in cert
        assert "codigo_verificacao" in cert
        assert "emitido_em" in cert
        codigo = cert["codigo_verificacao"]
        assert codigo.startswith("RC-")
        assert len(codigo) == 24  # RC-YYYY-XXXXXXXXXXXXXXXX (2+1+4+1+16), não enumerável

        # Armazena o código para o teste seguinte
        test_data["_codigo_cert"] = codigo

        # 3. Verifica o código publicamente (sem autenticação)
        verify_resp = await client.get(f"/api/v1/certificados/{codigo}/verificar")
        assert verify_resp.status_code == 200
        v = verify_resp.json()
        assert v["valido"] is True
        assert isinstance(v["aluno_nome"], str) and len(v["aluno_nome"]) > 0
        assert isinstance(v["curso"], str) and len(v["curso"]) > 0
        assert "emitido_em" in v

    async def test_certificado_duplicado_retorna_409(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Emitir certificado para a mesma matrícula novamente → 409."""
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CERTIFICADO_JA_EMITIDO"

    async def test_verificar_codigo_inexistente_retorna_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/certificados/RC-0000-ZZZZZZ/verificar")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CERTIFICADO_NAO_ENCONTRADO"

    async def test_emitir_sem_token_retorna_401(
        self, client: AsyncClient, test_data: dict
    ):
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}"
        )
        assert resp.status_code == 401

    async def test_emitir_matricula_alheia_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            f"/api/v1/certificados/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "MATRICULA_NAO_ENCONTRADA"
