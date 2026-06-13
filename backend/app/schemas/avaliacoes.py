import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AvaliacaoCreate(BaseModel):
    nota: int = Field(ge=1, le=5)
    texto: str | None = Field(default=None, max_length=1000)


class AvaliacaoMinha(BaseModel):
    """A avaliação do próprio aluno (para preencher o formulário)."""
    nota: int
    texto: str | None
    status: str


class AvaliacaoPublica(BaseModel):
    autor: str          # nome abreviado ("João S.") — privacidade
    nota: int
    texto: str | None
    criado_em: datetime


class AvaliacoesResponse(BaseModel):
    items: list[AvaliacaoPublica]
    media: float | None
    total: int
