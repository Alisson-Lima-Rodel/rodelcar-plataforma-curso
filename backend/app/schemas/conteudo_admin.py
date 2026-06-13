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
