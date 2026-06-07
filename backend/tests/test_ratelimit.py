"""Rate limiting é padrão de TODA a API (SlowAPIMiddleware + default_limits).

Validamos contra /health para provar que o teto vale app-wide, sem depender de
nenhum router específico. O limite é lido de settings a cada requisição, então
usamos um teto baixo próprio que não interfere nas demais rotas/testes.
"""
from httpx import AsyncClient


class TestRateLimit:
    async def test_excesso_de_requisicoes_retorna_429(
        self, client: AsyncClient, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "RATE_LIMIT_PUBLIC", "2/minute")

        r1 = await client.get("/health")
        r2 = await client.get("/health")
        r3 = await client.get("/health")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        body = r3.json()
        assert body["error"]["code"] == "RATE_LIMITED"
        assert r3.headers.get("Retry-After") == "60"

    async def test_rota_autenticada_tambem_limitada(
        self, client: AsyncClient, monkeypatch
    ):
        """O default vale também para rotas 🔒 — aqui sem token (401), mas o
        limite é avaliado antes e dispara 429 ao exceder o teto."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "RATE_LIMIT_PUBLIC", "2/minute")

        # bucket é por (rota, IP); usamos uma rota diferente da do outro teste.
        for _ in range(2):
            await client.get("/api/v1/me/matriculas")
        resp = await client.get("/api/v1/me/matriculas")

        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "RATE_LIMITED"

    async def test_login_tem_teto_estrito_anti_brute_force(self, client: AsyncClient):
        """/auth/login usa RATE_LIMIT_AUTH (5/min default), bem mais baixo que o
        teto público — trava brute-force mesmo com o IP dentro do limite geral."""
        creds = {"email": "naoexiste@rodelcar.dev", "senha": "x"}
        for _ in range(5):
            r = await client.post("/api/v1/auth/login", json=creds)
            assert r.status_code == 401
        r6 = await client.post("/api/v1/auth/login", json=creds)
        assert r6.status_code == 429
        assert r6.json()["error"]["code"] == "RATE_LIMITED"

    async def test_formato_invalido_nao_derruba_api(self, monkeypatch):
        """Valor de env mal formatado cai no default seguro, não em 500."""
        from app.core.ratelimit import _DEFAULT_LIMIT, _validated, public_limit
        from app.core.config import settings

        _validated.cache_clear()
        monkeypatch.setattr(settings, "RATE_LIMIT_PUBLIC", "100/min")  # inválido
        assert public_limit() == _DEFAULT_LIMIT
        _validated.cache_clear()
