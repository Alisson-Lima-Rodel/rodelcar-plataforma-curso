"""Extração de metadados do YouTube via oEmbed (sem chave de API).

oEmbed devolve título, autor (canal) e thumbnail de um vídeo público — só com a
URL. NÃO devolve duração nem nº de views (isso exige a YouTube Data API, com
chave/quota), então esses campos seguem manuais no cadastro.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

_OEMBED = "https://www.youtube.com/oembed"


async def buscar_metadados(youtube_url: str) -> dict | None:
    """Retorna {titulo, canal} do vídeo, ou None se indisponível (privado/erro).

    Best-effort: qualquer falha vira None — o cadastro segue com o que o admin
    digitou. Timeout curto para não travar o salvar.
    """
    if not youtube_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(
                _OEMBED, params={"url": youtube_url, "format": "json"}
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        logger.info("oEmbed indisponível para %s — cadastro segue manual.", youtube_url)
        return None
    return {
        "titulo": (data.get("title") or "").strip() or None,
        "canal": (data.get("author_name") or "").strip() or None,
    }
