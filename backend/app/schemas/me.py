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
    # Quando NÃO é autoatendível por anti-abuso (mas seria pelo prazo): direciona
    # ao suporte. RECURSO_CONSUMIDO (>20% assistido) | LIMITE_REEMBOLSOS.
    motivo_bloqueio: str | None = None
    # Curso ainda à venda (Curso.status == ativo): permite ao aluno com acesso
    # encerrado/expirado recomprar (botão "Comprar" → checkout). Se inativo, sem botão.
    curso_disponivel: bool = False


class MatriculaListResponse(BaseModel):
    items: list[MatriculaItem]


class CancelamentoResultado(BaseModel):
    matricula_id: uuid.UUID
    reembolsado: bool
    assinatura_cancelada: bool
    cursos_revogados: int


class MatriculaGratuitaResponse(BaseModel):
    matricula_id: uuid.UUID
    slug: str
    status: str
    ja_matriculado: bool  # já tinha matrícula (reativada) vs. nova


class CupomResumo(BaseModel):
    codigo: str
    tipo: str  # percentual | valor
    valor: float
    validade: datetime | None = None


class IndicacaoResponse(BaseModel):
    codigo: str  # código pessoal do aluno (para compartilhar)
    total_indicados: int
    total_recompensados: int
    cupons: list[CupomResumo]  # cupons ganhos (recompensas), ainda ativos


class UltimaAula(BaseModel):
    aula_id: uuid.UUID
    titulo: str
    curso_slug: str
    percentual: float
    # Id do embed do Panda (video_external_id) — o front monta a capa (preview)
    # da aula no card "Retomar de onde parou". None se a aula ainda não sincronizou.
    panda_external_id: str | None = None


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


class PlayerQuizResumo(BaseModel):
    id: uuid.UUID
    titulo: str
    aprovado: bool  # o aluno já passou neste quiz?


class PlayerModulo(BaseModel):
    id: uuid.UUID
    titulo: str
    ordem: int
    aulas: list[PlayerAula]
    quiz: PlayerQuizResumo | None = None  # quiz ATIVO do módulo (se houver)


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
    # Motivo de bloqueio do certificado quando o gate ainda impede mas não é só
    # "falta assistir/quiz" (ex.: aula sem duração cadastrada — oversight do admin).
    # Texto p/ a UI; None = sem bloqueio especial.
    cert_bloqueio: str | None = None
    certificado: CertificadoResumo | None = None
    modulos: list[PlayerModulo]
