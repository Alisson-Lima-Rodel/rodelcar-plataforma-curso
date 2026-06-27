"""Metadados do YouTube para o cadastro de vídeo.

Dois caminhos, do mais rico para o mais simples:
- **Data API v3** (se `YOUTUBE_API_KEY` setada): título, canal, **duração, views
  e likes**. Custa 1 unidade de cota por vídeo (cota diária grátis = 10 mil).
- **oEmbed** (sem chave): só título e canal (e a capa sai da própria URL no front).

Best-effort: qualquer falha/ausência de chave cai no caminho seguinte ou em None,
e o cadastro segue com o que o admin digitou. YouTube não expõe dislikes (2021+).
"""

import logging
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_OEMBED = "https://www.youtube.com/oembed"
_DATA_API = "https://www.googleapis.com/youtube/v3/videos"


def youtube_id(url: str | None) -> str | None:
    """id de 11 chars de watch/youtu.be/embed/shorts/live (ou o id puro)."""
    if not url:
        return None
    url = url.strip()
    m = re.search(
        r"(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|v/|live/))([\w-]{11})",
        url,
    )
    if m:
        return m.group(1)
    return url if re.fullmatch(r"[\w-]{11}", url) else None


def _fmt_duracao(iso: str | None) -> str | None:
    """ISO 8601 (PT3M31S) → '03:31' / '1:02:03'."""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return f"{h}:{mi:02d}:{s:02d}" if h else f"{mi:02d}:{s:02d}"


def _fmt_contagem(valor) -> str | None:
    """12345 → '12,3 mil'; 1500000 → '1,5 mi'; 966 → '966'."""
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}".replace(".", ",") + " mil"
    return f"{n / 1_000_000:.1f}".replace(".", ",") + " mi"


async def _via_oembed(url: str) -> dict | None:
    # Só chama o oEmbed se for mesmo uma URL do YouTube (consistente com a Data
    # API; evita requisição de rede para entradas que não são do YouTube).
    if youtube_id(url) is None:
        return None
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(_OEMBED, params={"url": url, "format": "json"})
            r.raise_for_status()
            data = r.json()
    except Exception:
        logger.info("oEmbed indisponível para %s.", url)
        return None
    return {
        "titulo": (data.get("title") or "").strip() or None,
        "canal": (data.get("author_name") or "").strip() or None,
    }


async def _via_data_api(url: str) -> dict | None:
    vid = youtube_id(url)
    if not vid:
        return None
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(
                _DATA_API,
                params={
                    "part": "snippet,contentDetails,statistics",
                    "id": vid,
                    "key": settings.YOUTUBE_API_KEY,
                },
            )
            r.raise_for_status()
            items = r.json().get("items") or []
    except Exception:
        logger.warning("YouTube Data API falhou para %s — caindo no oEmbed.", url)
        return None
    if not items:
        return None
    it = items[0]
    sn = it.get("snippet") or {}
    cd = it.get("contentDetails") or {}
    st = it.get("statistics") or {}
    return {
        "titulo": (sn.get("title") or "").strip() or None,
        "canal": (sn.get("channelTitle") or "").strip() or None,
        "duracao": _fmt_duracao(cd.get("duration")),
        "views": _fmt_contagem(st.get("viewCount")),
        "likes": _fmt_contagem(st.get("likeCount")),  # ausente se o dono ocultou
    }


async def buscar_metadados(url: str) -> dict | None:
    """Melhores metadados disponíveis. Com chave → Data API (duração/views/likes);
    sem chave ou em falha → oEmbed (título/canal). None se nada deu certo."""
    if not url:
        return None
    if settings.YOUTUBE_API_KEY:
        dados = await _via_data_api(url)
        if dados:
            return dados
    return await _via_oembed(url)


async def verificar_disponibilidade(url: str) -> bool | None:
    """O vídeo ainda existe e é público no YouTube?

    True = disponível; False = apagado/privado (404/401/403 no oEmbed, ou `items`
    vazio na Data API); None = não dá pra saber (rede/timeout, ou não é YouTube) —
    NUNCA esconder por None, só por False. Usa oEmbed (não precisa de chave); o
    oEmbed responde 404 p/ vídeo inexistente e 401 p/ privado/embed desabilitado.
    """
    if youtube_id(url) is None:
        return None
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(_OEMBED, params={"url": url, "format": "json"})
    except Exception:
        logger.info("oEmbed indisponível p/ checar disponibilidade de %s.", url)
        return None
    if r.status_code == 200:
        return True
    if r.status_code in (401, 403, 404):
        return False
    return None  # 5xx/429/etc.: transitório — não esconde
