import uuid

from pydantic import BaseModel, Field


class ProgressoRequest(BaseModel):
    aula_id: uuid.UUID
    percentual: float = Field(ge=0, le=100)
    concluida: bool


class ProgressoResponse(BaseModel):
    aula_id: uuid.UUID
    percentual: float
    concluida: bool
    curso_percentual: float
