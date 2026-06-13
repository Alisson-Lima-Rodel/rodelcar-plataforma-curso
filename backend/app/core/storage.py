"""Upload de imagens para o Supabase Storage (capas de curso).

Bucket público: a URL retornada é a pública/CDN do Supabase, salva em
`cursos.thumbnail_url` e carregada direto pelo navegador (front na Vercel).
A `service_role` key vive só no backend (nunca exposta ao front).

Segurança do upload:
- **Só raster** (PNG/JPG/WebP) vindo do admin — SVG é recusado (pode embutir
  `<script>` → XSS). As capas SVG da marca entram só pelo script interno
  (`seed_capas.py`), que passa `formatos=FORMATOS_SVG` por ser código confiável.
- **Magic bytes**: o conteúdo real é conferido contra o tipo declarado (impede
  enviar um script com Content-Type: image/png).
- **Teto de 5 MB** (também limitado na leitura do request, no router).
"""

import logging
import uuid

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024  # 5 MB

# Formatos aceitos no upload do ADMIN (raster — sem SVG/GIF animado).
FORMATOS_RASTER = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
# Usado só pelo seed interno (arte SVG da marca, confiável).
FORMATOS_SVG = {"image/svg+xml": "svg"}

EXTS_PERMITIDAS_LABEL = "PNG, JPG ou WebP"


class StorageError(Exception):
    """Falha de validação ou de upload — o router traduz para o envelope padrão."""


def storage_ativo() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)


def _tipo_real(conteudo: bytes) -> str | None:
    """Detecta o tipo pelos bytes iniciais (não confia no Content-Type)."""
    if conteudo[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if conteudo[:3] == b"\xff\xd8\xff":
        return "jpg"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "webp"
    cabeca = conteudo[:512].lstrip().lower()
    if cabeca.startswith(b"<?xml") or cabeca.startswith(b"<svg"):
        return "svg"
    return None


async def upload_imagem(
    conteudo: bytes,
    content_type: str | None,
    prefixo: str = "cursos",
    *,
    formatos: dict[str, str] = FORMATOS_RASTER,
) -> str:
    """Valida (formato declarado, tamanho e bytes reais) e sobe; devolve a URL pública."""
    ct = (content_type or "").split(";")[0].strip().lower()
    ext = formatos.get(ct)
    if ext is None:
        rotulos = ", ".join(sorted({v.upper() for v in formatos.values()}))
        raise StorageError(f"Formato não permitido. Aceitos: {rotulos}.")
    if not conteudo:
        raise StorageError("Arquivo vazio.")
    if len(conteudo) > MAX_BYTES:
        raise StorageError("Imagem acima de 5 MB.")
    if _tipo_real(conteudo) != ext:
        raise StorageError("O arquivo não corresponde a uma imagem válida do tipo informado.")

    if not storage_ativo():
        raise StorageError("Storage de imagens não configurado.")

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
                    "Content-Type": ct,
                    "x-upsert": "true",
                },
            )
            r.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Falha no upload para o Supabase Storage")
        raise StorageError("Não foi possível enviar a imagem ao storage.") from exc

    return f"{base}/storage/v1/object/public/{bucket}/{caminho}"
