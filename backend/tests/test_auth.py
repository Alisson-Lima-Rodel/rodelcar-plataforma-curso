import pytest
from httpx import AsyncClient


# ── POST /api/v1/auth/login ───────────────────────────────────────────────────
class TestLogin:
    async def test_teto_de_falhas_por_conta_429(self, client: AsyncClient, monkeypatch):
        """Após o teto de FALHAS na MESMA conta, novas tentativas tomam 429 (teto
        por conta, além do teto por IP). Conta inexistente → sempre falha."""
        from app.core import ratelimit

        # Teto por conta < teto por IP (5/min) para o 429 vir da conta no teste.
        monkeypatch.setattr(ratelimit.settings, "RATE_LIMIT_AUTH_ACCOUNT", "2/minute")
        ratelimit.reset_conta()
        creds = {"email": "brute_conta@rodelcar.dev", "senha": "errada"}
        assert (await client.post("/api/v1/auth/login", json=creds)).status_code == 401
        assert (await client.post("/api/v1/auth/login", json=creds)).status_code == 401
        r = await client.post("/api/v1/auth/login", json=creds)
        assert r.status_code == 429
        assert r.json()["error"]["code"] == "RATE_LIMITED"

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

    async def test_reuso_invalida_access_token(
        self, client: AsyncClient, test_aluno: dict
    ):
        """Detecção de reuso bumpa token_version → o access token vivo é invalidado."""
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        access = login.json()["access_token"]
        old_refresh = login.json()["refresh_token"]
        h = {"Authorization": f"Bearer {access}"}
        assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 200

        # rotaciona e reusa o token antigo → reuso/roubo → bump token_version
        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

        # o access token capturado (tv defasado) agora é rejeitado
        resp = await client.get("/api/v1/auth/me", headers=h)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"

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

        # Token apagado no logout não renova mais (e não dispara wipe de roubo).
        r = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "REFRESH_INVALIDO"

    async def test_logout_invalida_access_token(
        self, client: AsyncClient, test_aluno: dict
    ):
        """Logout derruba a sessão na hora: o access token vivo deixa de valer
        (token_version incrementado), não só o refresh — sai de todos os aparelhos."""
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_aluno["email"], "senha": test_aluno["password"]},
        )
        access = login.json()["access_token"]
        refresh = login.json()["refresh_token"]
        h = {"Authorization": f"Bearer {access}"}
        assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 200
        out = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
        assert out.status_code == 204
        # access token morre imediatamente (não espera o exp de ~30min)
        assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 401

    async def test_logout_replay_nao_derruba_sessao_nova(
        self, client: AsyncClient, test_aluno: dict
    ):
        """Reapresentar um refresh já usado no logout é no-op: NÃO dispara wipe nem
        derruba uma sessão nova (sem DoS de sessão por replay)."""
        creds = {"email": test_aluno["email"], "senha": test_aluno["password"]}
        r_old = (await client.post("/api/v1/auth/login", json=creds)).json()["refresh_token"]
        await client.post("/api/v1/auth/logout", json={"refresh_token": r_old})
        # nova sessão (após o logout)
        h2 = {"Authorization": f"Bearer {(await client.post('/api/v1/auth/login', json=creds)).json()['access_token']}"}
        assert (await client.get("/api/v1/auth/me", headers=h2)).status_code == 200
        # replay do token antigo no logout → no-op
        assert (await client.post("/api/v1/auth/logout", json={"refresh_token": r_old})).status_code == 204
        # a sessão NOVA continua válida (não foi derrubada pelo replay)
        assert (await client.get("/api/v1/auth/me", headers=h2)).status_code == 200


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
