import uuid

from pydantic import BaseModel, ConfigDict


class VideoPublico(BaseModel):
    """Vídeo ativo exibido na prova social (sem status/ordem)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    youtube_url: str | None = None
    duracao: str | None = None
    views: str | None = None


class FaqPublico(BaseModel):
    """Pergunta frequente ativa, exibida na página de venda."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pergunta: str
    resposta: str
