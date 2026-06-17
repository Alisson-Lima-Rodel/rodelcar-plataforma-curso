import uuid

from pydantic import BaseModel, Field


class ProgressoRequest(BaseModel):
    aula_id: uuid.UUID
    percentual: float = Field(ge=0, le=100)
    concluida: bool
    # Último segundo assistido (resume). None = não mexe na posição (ex.: o botão
    # "Concluir" não deve zerar onde o aluno parou). `segundos_assistidos` é
    # server-only (anti-fraude) e NUNCA vem do cliente.
    posicao_segundos: int | None = Field(default=None, ge=0)


class ProgressoResponse(BaseModel):
    aula_id: uuid.UUID
    percentual: float
    concluida: bool
    curso_percentual: float
    posicao_segundos: int = 0
