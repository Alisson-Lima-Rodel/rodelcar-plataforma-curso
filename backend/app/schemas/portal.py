import uuid

from pydantic import BaseModel, ConfigDict


class VideoPublico(BaseModel):
    """Vídeo ativo exibido na prova social (sem status/ordem)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    youtube_url: str | None = None
    canal: str | None = None
    duracao: str | None = None
    views: str | None = None
    likes: str | None = None
    estrelas: int = 5


class FaqPublico(BaseModel):
    """Pergunta frequente ativa, exibida na página de venda."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pergunta: str
    resposta: str


class GoogleReviewItem(BaseModel):
    autor: str | None = None
    nota: int | None = None
    texto: str | None = None
    quando: str | None = None


class GoogleReviewsPublico(BaseModel):
    """Nota e avaliações da ficha do Google (prova social)."""

    rating: float | None = None
    total: int = 0
    reviews: list[GoogleReviewItem] = []
