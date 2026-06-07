import pytest
from httpx import AsyncClient


# ── POST /api/v1/auth/login ───────────────────────────────────────────────────
class TestLogin:
    async def test_login_valido_retorna_tokens(
        self, client: AsyncClient, test_aluno: dict
    ):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800  # 30 min × 60 s

    async def test_login_senha_errada_retorna_401(
        self, client: AsyncClient, test_aluno: dict
    ):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": "senha_errada"},
        )
        assert resp.status_code == 401
        error = resp.json()["error"]
        assert error["code"] == "CREDENCIAIS_INVALIDAS"

    async def test_login_email_inexistente_retorna_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "naoexiste@rodelcar.dev", "senha": "qualquer"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "CREDENCIAIS_INVALIDAS"

    async def test_login_email_invalido_retorna_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nao-e-email", "senha": "abc"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ── POST /api/v1/auth/refresh ─────────────────────────────────────────────────
class TestRefresh:
    async def test_refresh_valido_retorna_novos_tokens(
        self, client: AsyncClient, test_aluno: dict
    ):
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        refresh_token = login.json()["refresh_token"]

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_token_invalido_retorna_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "token.invalido.aqui"}
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "REFRESH_INVALIDO"

    async def test_refresh_com_access_token_retorna_401(
        self, client: AsyncClient, test_aluno: dict
    ):
        """Usar access_token como refresh deve ser rejeitado (type != refresh)."""
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        access_token = login.json()["access_token"]

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": access_token}
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "REFRESH_INVALIDO"

    async def test_refresh_rotaciona_e_detecta_reuso(
        self, client: AsyncClient, test_aluno: dict
    ):
        """Rotação: refresh invalida o token usado. Reapresentá-lo = reuso/roubo,
        revoga TODA a família (inclusive o token novo)."""
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        old_refresh = login.json()["refresh_token"]

        r1 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert r1.status_code == 200
        new_refresh = r1.json()["refresh_token"]
        assert new_refresh != old_refresh

        # Reuso do token antigo (já rotacionado) → 401 + revoga família.
        r2 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert r2.status_code == 401
        assert r2.json()["error"]["code"] == "REFRESH_REUTILIZADO"

        # O token novo também foi revogado pela detecção de reuso.
        r3 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": new_refresh}
        )
        assert r3.status_code == 401

    async def test_logout_revoga_refresh(
        self, client: AsyncClient, test_aluno: dict
    ):
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        refresh_token = login.json()["refresh_token"]

        out = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh_token}
        )
        assert out.status_code == 204

        # Token revogado não renova mais.
        r = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "REFRESH_REUTILIZADO"


# ── GET /api/v1/auth/me ───────────────────────────────────────────────────────
class TestMe:
    async def test_me_autenticado_retorna_dados(
        self, client: AsyncClient, test_aluno: dict, auth_headers: dict
    ):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_aluno["email"]
        assert data["id"] == test_aluno["id"]
        assert isinstance(data["matriculas_ativas"], int)

    async def test_me_sem_token_retorna_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "NAO_AUTENTICADO"

    async def test_me_token_invalido_retorna_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer token.completamente.invalido"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"

    async def test_me_usando_refresh_token_retorna_401(
        self, client: AsyncClient, test_aluno: dict
    ):
        """refresh_token não deve funcionar em rotas protegidas (type != access)."""
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        refresh_token = login.json()["refresh_token"]

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"
