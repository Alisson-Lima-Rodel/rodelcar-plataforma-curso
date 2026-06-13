"""Nota e avaliações da ficha do Google (Places API v1).

Best-effort, igual ao YouTube: sem chave/Place ID, devolve None e o bloco some
do portal. Um job diário grava em `GoogleReviewCache`; o endpoint público lê do
cache (não bate na API a cada visita — cota/custo do Places).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import GoogleReviewCache

logger = logging.getLogger(__name__)

_PLACES_URL = "https://places.googleapis.com/v1/places/{place_id}"
_FIELD_MASK = "rating,userRatingCount,reviews"
_MAX_REVIEWS = 6


def google_ativo() -> bool:
    return bool(settings.GOOGLE_PLACES_API_KEY and settings.GOOGLE_PLACE_ID)


def _parse_place(data: dict) -> dict:
    """Normaliza a resposta da Place Details no formato do cache."""
    reviews = []
    for rv in (data.get("reviews") or [])[:_MAX_REVIEWS]:
        reviews.append({
            "autor": (rv.get("authorAttribution") or {}).get("displayName"),
            "nota": rv.get("rating"),
            "texto": (rv.get("text") or {}).get("text"),
            "quando": rv.get("relativePublishTimeDescription"),
        })
    return {
        "rating": data.get("rating"),
        "total": int(data.get("userRatingCount") or 0),
        "reviews": reviews,
    }


async def buscar_da_api() -> dict | None:
    """Consulta a Place Details. None se desativado ou em falha de rede."""
    if not google_ativo():
        return None
    url = _PLACES_URL.format(place_id=settings.GOOGLE_PLACE_ID)
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                url,
                headers={
                    "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
                    "X-Goog-FieldMask": _FIELD_MASK,
                },
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        logger.warning("Google Places API indisponível.")
        return None
    return _parse_place(data)


async def atualizar_cache(db: AsyncSession) -> bool:
    """Atualiza a linha única do cache. False se nada foi buscado (mantém o antigo)."""
    dados = await buscar_da_api()
    if dados is None:
        return False
    row = await db.get(GoogleReviewCache, 1)
    if row is None:
        row = GoogleReviewCache(id=1)
        db.add(row)
    row.rating = dados["rating"]
    row.total = dados["total"]
    row.reviews = dados["reviews"]
    row.atualizado_em = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Cache de avaliações do Google atualizado (%d avaliações).", row.total)
    return True
