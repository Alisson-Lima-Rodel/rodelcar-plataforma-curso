"""Avaliações do Google: parsing, cache e endpoint público."""
from httpx import AsyncClient

from app.core import google_reviews
from app.core.db import AsyncSessionLocal
from app.models import GoogleReviewCache

_PLACE_PAYLOAD = {
    "rating": 4.8,
    "userRatingCount": 137,
    "reviews": [
        {
            "rating": 5,
            "text": {"text": "Resolveram meu Dualogic na hora."},
            "authorAttribution": {"displayName": "Carlos M."},
            "relativePublishTimeDescription": "há 2 semanas",
        },
        {
            "rating": 4,
            "text": {"text": "Bom atendimento."},
            "authorAttribution": {"displayName": "Ana P."},
            "relativePublishTimeDescription": "há 1 mês",
        },
    ],
}


def test_parse_place():
    out = google_reviews._parse_place(_PLACE_PAYLOAD)
    assert out["rating"] == 4.8
    assert out["total"] == 137
    assert len(out["reviews"]) == 2
    assert out["reviews"][0]["autor"] == "Carlos M."
    assert out["reviews"][0]["nota"] == 5
    assert "Dualogic" in out["reviews"][0]["texto"]


def test_parse_place_vazio():
    out = google_reviews._parse_place({})
    assert out["rating"] is None and out["total"] == 0 and out["reviews"] == []


class TestGoogleReviewsEndpoint:
    async def _limpar(self):
        async with AsyncSessionLocal() as db:
            row = await db.get(GoogleReviewCache, 1)
            if row:
                await db.delete(row)
                await db.commit()

    async def test_vazio_sem_cache(self, client: AsyncClient):
        await self._limpar()
        resp = await client.get("/api/v1/google-reviews")
        assert resp.status_code == 200
        d = resp.json()
        assert d["total"] == 0 and d["rating"] is None and d["reviews"] == []

    async def test_atualizar_cache_e_ler(self, client: AsyncClient, monkeypatch):
        async def fake_buscar():
            return google_reviews._parse_place(_PLACE_PAYLOAD)

        monkeypatch.setattr(google_reviews, "buscar_da_api", fake_buscar)
        async with AsyncSessionLocal() as db:
            ok = await google_reviews.atualizar_cache(db)
        assert ok is True

        resp = await client.get("/api/v1/google-reviews")
        d = resp.json()
        assert d["rating"] == 4.8 and d["total"] == 137
        assert d["reviews"][0]["autor"] == "Carlos M."
        await self._limpar()

    async def test_atualizar_sem_config_nao_grava(self, monkeypatch):
        # google_ativo() False → buscar_da_api None → atualizar_cache False
        monkeypatch.setattr(google_reviews.settings, "GOOGLE_PLACES_API_KEY", "")
        monkeypatch.setattr(google_reviews.settings, "GOOGLE_PLACE_ID", "")
        assert await google_reviews.buscar_da_api() is None
        async with AsyncSessionLocal() as db:
            assert await google_reviews.atualizar_cache(db) is False
