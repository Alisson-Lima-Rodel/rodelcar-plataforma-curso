"""Validação do upload de imagem (formato, tamanho, magic bytes) — sem rede.

Todas as recusas acontecem ANTES da chamada ao Supabase, então não há I/O.
"""
import pytest

from app.core.config import settings
from app.core.storage import (
    FORMATOS_RASTER,
    FORMATOS_SVG,
    MAX_BYTES,
    StorageError,
    upload_imagem,
)


@pytest.fixture
def storage_off(monkeypatch):
    """Garante que a validação não chegue à rede: storage 'não configurado'.

    O container de teste recebe as credenciais reais do Supabase via compose;
    sem isto, os casos de input VÁLIDO subiriam um arquivo de verdade no bucket.
    """
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "")

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPG = b"\xff\xd8\xff" + b"0" * 64
SVG = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"


class TestValidacaoUpload:
    async def test_formato_nao_aceito(self):
        with pytest.raises(StorageError, match="Formato não permitido"):
            await upload_imagem(PNG, "image/gif")

    async def test_svg_recusado_no_raster(self):
        # SVG (XSS) não pode entrar pelo caminho do admin (FORMATOS_RASTER).
        with pytest.raises(StorageError, match="Formato não permitido"):
            await upload_imagem(SVG, "image/svg+xml")

    async def test_acima_de_5mb(self):
        grande = PNG + b"0" * (MAX_BYTES + 1)
        with pytest.raises(StorageError, match="5 MB"):
            await upload_imagem(grande, "image/png")

    async def test_magic_byte_nao_bate(self):
        # Content-Type diz PNG mas o conteúdo é texto/script → recusado.
        with pytest.raises(StorageError, match="não corresponde"):
            await upload_imagem(b"<script>alert(1)</script>", "image/png")

    async def test_jpeg_valido_passa_validacao(self, storage_off):
        # Tipo declarado e magic batem; para só no gate de config (sem rede).
        with pytest.raises(StorageError, match="não configurado"):
            await upload_imagem(JPG, "image/jpeg")

    async def test_svg_confiavel_passa_validacao(self, storage_off):
        # Pelo conjunto FORMATOS_SVG (seed interno) o SVG é aceito na validação.
        with pytest.raises(StorageError, match="não configurado"):
            await upload_imagem(SVG, "image/svg+xml", formatos=FORMATOS_SVG)

    def test_raster_nao_inclui_svg(self):
        assert "image/svg+xml" not in FORMATOS_RASTER
