"""Cliente da REST API do Panda Video (server-side).

A `PANDA_API_KEY` fica SÓ aqui (backend) — o upload é mediado: o backend cria a
sessão TUS (a chave vai no Upload-Metadata, server-to-server) e devolve só a URL
de upload; o browser envia o arquivo para essa URL, sem nunca ver a chave.

Endpoints (confirmados na doc oficial):
- Upload TUS (2 passos): POST {uploader}/files  → Location p/ o PATCH do arquivo.
- Propriedades:          GET  https://api-v2.pandavideo.com.br/videos/{id}
- Retenção:              GET  https://data.pandavideo.com/retention/{id}
- DRM:                   JWT (HS256) assinado com o segredo do watermark group,
                         anexado ao embed como ?watermark=...&drm_group_id=...
Header de auth: `Authorization: <API_KEY>` (SEM "Bearer").
"""

import base64
import logging
import time
import uuid

import httpx
import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api-v2.pandavideo.com.br"
DATA_BASE = "https://data.pandavideo.com"


class PandaIndisponivel(Exception):
    """Falha ao falar com o Panda (sem chave, rede ou erro HTTP). Vira 502/503."""


def _auth_headers() -> dict[str, str]:
    return {"Authorization": settings.PANDA_API_KEY}


def _exigir_chave() -> None:
    if not settings.panda_ativo:
        raise PandaIndisponivel("PANDA_API_KEY não configurada.")


def _b64(valor: str) -> str:
    return base64.b64encode(valor.encode()).decode()


async def criar_upload(
    *,
    filename: str,
    size: int,
    video_id: str | None = None,
    folder_id: str | None = None,
) -> dict:
    """Cria a sessão de upload TUS (passo 1). Retorna {video_id, upload_url}.

    O `video_id` (UUID v4) é o id definitivo do vídeo no Panda — geramos aqui e já
    o gravamos na aula; o browser sobe o arquivo via PATCH na `upload_url`.
    """
    _exigir_chave()
    vid = video_id or str(uuid.uuid4())
    pares = {
        "authorization": settings.PANDA_API_KEY,
        "filename": filename,
        "video_id": vid,
    }
    folder = folder_id or settings.PANDA_FOLDER_ID
    if folder:
        pares["folder_id"] = folder
    upload_metadata = ",".join(f"{k} {_b64(v)}" for k, v in pares.items())

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{settings.PANDA_UPLOADER_BASE}/files",
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Length": str(size),
                    "Upload-Metadata": upload_metadata,
                },
            )
            r.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Panda: falha ao criar upload TUS: %s", exc)
        raise PandaIndisponivel("Falha ao criar o upload no Panda.") from exc

    location = r.headers.get("Location") or r.headers.get("location")
    if not location:
        raise PandaIndisponivel("Panda não retornou a URL de upload (Location).")
    return {"video_id": vid, "upload_url": location}


async def obter_video(video_id: str) -> dict:
    """GET /videos/{id} — propriedades (length, thumbnail, status, subtitles…)."""
    _exigir_chave()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{API_BASE}/videos/{video_id}", headers=_auth_headers()
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as exc:
        logger.warning("Panda: falha ao obter vídeo %s: %s", video_id, exc)
        raise PandaIndisponivel("Falha ao consultar o vídeo no Panda.") from exc


async def retencao(
    video_id: str, *, start_date: str | None = None, end_date: str | None = None
) -> dict:
    """GET /retention/{id} — curva de retenção (seg → % de espectadores)."""
    _exigir_chave()
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                f"{DATA_BASE}/retention/{video_id}",
                headers=_auth_headers(),
                params=params,
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as exc:
        logger.warning("Panda: falha na retenção de %s: %s", video_id, exc)
        raise PandaIndisponivel("Falha ao consultar a retenção no Panda.") from exc


def assinar_drm_token(ttl: int | None = None) -> str | None:
    """JWT (HS256) do watermark group p/ embed privado. None se DRM desligado.

    Anexado ao embed como ?watermark=<jwt>&drm_group_id=<id>.
    """
    if not settings.panda_drm_ativo:
        return None
    ttl = ttl or settings.PANDA_DRM_TOKEN_TTL
    payload = {
        "drm_group_id": settings.PANDA_DRM_GROUP_ID,
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(payload, settings.PANDA_DRM_SECRET, algorithm="HS256")


def duracao_segundos(video: dict) -> int | None:
    """`length` (segundos) das propriedades do vídeo, se houver."""
    v = video.get("length")
    return int(v) if isinstance(v, (int, float)) else None


def thumbnail_url(video: dict) -> str | None:
    return video.get("thumbnail") or None


def pontos_retencao(data: dict) -> list[dict]:
    """Converte o mapa `retention` ({"0":100,"5":95,…}) numa lista ordenada de
    {segundo, percentual} — pronta para o gráfico do admin."""
    ret = data.get("retention") or {}
    pontos: list[dict] = []
    for chave, valor in ret.items():
        try:
            seg = int(chave)
            pct = float(valor)
        except (TypeError, ValueError):
            continue
        pontos.append({"segundo": seg, "percentual": pct})
    pontos.sort(key=lambda p: p["segundo"])
    return pontos
