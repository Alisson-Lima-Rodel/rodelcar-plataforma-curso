import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import StatusMatricula


class CursoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    titulo: str


class MatriculaItem(BaseModel):
    id: uuid.UUID
    curso: CursoResumo
    status: StatusMatricula
    data_inicio: datetime
    data_expiracao: datetime
    dias_restantes: int
    progresso_percentual: float


class MatriculaListResponse(BaseModel):
    items: list[MatriculaItem]


class UltimaAula(BaseModel):
    aula_id: uuid.UUID
    titulo: str
    curso_slug: str
    percentual: float


class Alerta(BaseModel):
    tipo: str
    nivel: str
    mensagem: str


class ResumoDashboard(BaseModel):
    cursos_ativos: int
    aulas_concluidas: int
    certificados: int


class DashboardResponse(BaseModel):
    ultima_aula: UltimaAula | None
    alertas: list[Alerta]
    resumo: ResumoDashboard
