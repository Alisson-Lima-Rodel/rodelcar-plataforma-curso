import uuid

from pydantic import BaseModel, ConfigDict

from app.models import TipoCurso


# ── GET /cursos ───────────────────────────────────────────────────────────────
class CursoListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    titulo: str
    descricao_curta: str | None = None
    tipo: TipoCurso
    preco: float
    validade_dias: int
    thumbnail_url: str | None = None
    total_modulos: int
    total_aulas: int
    destaque: bool


class CursoListResponse(BaseModel):
    items: list[CursoListItem]
    total: int
    page: int
    size: int


# ── GET /cursos/{slug} ────────────────────────────────────────────────────────
class ModuloResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    ordem: int
    total_aulas: int


class CursoDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    titulo: str
    descricao: str | None = None
    tipo: TipoCurso
    preco: float
    validade_dias: int
    thumbnail_url: str | None = None
    modulos: list[ModuloResumo]
