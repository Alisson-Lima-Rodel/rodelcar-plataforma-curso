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
    # Direito de arrependimento (7 dias da compra, CDC art. 49)
    origem: str = "avulsa"  # avulsa | assinatura | manual
    cancelavel: bool = False
    cancelavel_ate: datetime | None = None


class MatriculaListResponse(BaseModel):
    items: list[MatriculaItem]


class CancelamentoResultado(BaseModel):
    matricula_id: uuid.UUID
    reembolsado: bool
    assinatura_cancelada: bool
    cursos_revogados: int


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


# ── Player do curso (estrutura + progresso por aula) ──────────────────────────
class PlayerAula(BaseModel):
    id: uuid.UUID
    titulo: str
    duracao_label: str
    concluida: bool
    percentual: float


class PlayerModulo(BaseModel):
    id: uuid.UUID
    titulo: str
    ordem: int
    aulas: list[PlayerAula]


class CertificadoResumo(BaseModel):
    codigo: str
    emitido_em: datetime


class PlayerCursoResponse(BaseModel):
    matricula_id: uuid.UUID
    curso: CursoResumo
    horas: str | None = None
    status: StatusMatricula
    progresso_percentual: float
    concluido: bool
    certificado: CertificadoResumo | None = None
    modulos: list[PlayerModulo]
