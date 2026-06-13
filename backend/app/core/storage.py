"""Upload de imagens para o Supabase Storage (capas de curso).

Bucket público: a URL retornada é a pública/CDN do Supabase, salva em
`cursos.thumbnail_url` e carregada direto pelo navegador (front na Vercel).
A `service_role` key vive só no backend (nunca exposta ao front).
"""

import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# content-type → extensão aceita
_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "image/gif": "gif",
}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


class StorageError(Exception):
    """Falha de validação ou de upload — o router traduz para o envelope padrão."""


def storage_ativo() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)


async def upload_imagem(conteudo: bytes, content_type: str | None, prefixo: str = "cursos") -> str:
    """Sobe a imagem e devolve a URL pública. Valida tipo e tamanho."""
    if not storage_ativo():
        raise StorageError("Storage de imagens não configurado.")
    ext = _EXT.get((content_type or "").split(";")[0].strip().lower())
    if ext is None:
        raise StorageError("Formato não suportado (use JPG, PNG, WebP, GIF ou SVG).")
    if not conteudo:
        raise StorageError("Arquivo vazio.")
    if len(conteudo) > MAX_BYTES:
        raise StorageError("Imagem acima de 5 MB.")

    base = settings.SUPABASE_URL.rstrip("/")
    bucket = settings.SUPABASE_BUCKET
    caminho = f"{prefixo}/{uuid.uuid4().hex}.{ext}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{base}/storage/v1/object/{bucket}/{caminho}",
                content=conteudo,
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
            )
            r.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Falha no upload para o Supabase Storage")
        raise StorageError("Não foi possível enviar a imagem ao storage.") from exc

    return f"{base}/storage/v1/object/public/{bucket}/{caminho}"
