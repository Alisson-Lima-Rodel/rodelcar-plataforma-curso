"""Schemas da gestão de conteúdo (módulos/aulas) no painel admin."""
import uuid

from pydantic import BaseModel, Field


class AulaAdmin(BaseModel):
    id: uuid.UUID
    titulo: str
    panda_video_id: str | None = None
    duracao_segundos: int
    ordem: int
    gratuita: bool


class ModuloAdmin(BaseModel):
    id: uuid.UUID
    titulo: str
    ordem: int
    aulas: list[AulaAdmin]


class ModuloCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    ordem: int = 0


class ModuloUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    ordem: int | None = None


class AulaCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    panda_video_id: str | None = Field(default=None, max_length=120)
    duracao_segundos: int = Field(default=0, ge=0)
    ordem: int = 0
    gratuita: bool = False


class AulaUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    panda_video_id: str | None = Field(default=None, max_length=120)
    duracao_segundos: int | None = Field(default=None, ge=0)
    ordem: int | None = None
    gratuita: bool | None = None


# ── Upload de vídeo pela tela admin (mediado pelo backend) ───────────────────
class AulaUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    # Teto (50 GB) p/ não repassar um Upload-Length absurdo ao TUS do Panda
    # (sessões fantasma/billing). Folgado p/ qualquer aula real; barra abuso.
    size: int = Field(gt=0, le=50 * 1024 * 1024 * 1024)  # bytes; vira Upload-Length
    content_type: str | None = Field(default=None, max_length=120)


class AulaUploadResponse(BaseModel):
    """O backend cria a sessão (com a chave) e devolve só a URL — o browser sobe
    o arquivo direto para `upload_url` (PATCH TUS), sem ver a PANDA_API_KEY."""
    video_id: str
    upload_url: str


class AulaSyncResponse(BaseModel):
    """Resultado da sincronização com o Panda (duração/capa/status)."""
    panda_video_id: str | None = None
    status: str | None = None
    duracao_segundos: int
    thumbnail: str | None = None


# ── Biblioteca do Panda (seletor de vídeo já existente) ──────────────────────
class PandaVideoItem(BaseModel):
    """Item da biblioteca do Panda, para escolher um vídeo já existente."""
    id: str
    titulo: str
    duracao_segundos: int | None = None
    thumbnail: str | None = None
    status: str | None = None


class PandaBibliotecaResponse(BaseModel):
    itens: list[PandaVideoItem]
    page: int
    limit: int


class PandaPastaItem(BaseModel):
    id: str
    nome: str


class PandaPastasResponse(BaseModel):
    itens: list[PandaPastaItem]


# ── Analytics de retenção (Panda) ────────────────────────────────────────────
class RetencaoPonto(BaseModel):
    segundo: int
    percentual: float  # % de espectadores ainda assistindo nesse segundo


class RetencaoResponse(BaseModel):
    panda_video_id: str
    duracao_segundos: int | None = None
    pontos: list[RetencaoPonto]
