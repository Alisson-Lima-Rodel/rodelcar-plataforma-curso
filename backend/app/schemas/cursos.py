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
    preco_antigo: float | None = None
    validade_dias: int
    thumbnail_url: str | None = None
    gratuito: bool = False  # curso 100% grátis (matrícula free)
    total_modulos: int
    total_aulas: int
    tem_preview: bool = False  # tem ao menos uma aula grátis
    destaque: bool
    # marketing / vitrine
    tagline: str | None = None
    horas: str | None = None
    aulas_total: int = 0
    rating: float | None = None
    alunos: int = 0
    nivel: str | None = None
    icon: str | None = None
    badge_label: str | None = None


class CursoListResponse(BaseModel):
    items: list[CursoListItem]
    total: int
    page: int
    size: int


# ── GET /cursos/{slug} ────────────────────────────────────────────────────────
class AulaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    duracao_label: str  # "12:40"
    gratuita: bool = False  # liberada como preview na página de venda


class AulaPreview(BaseModel):
    """Aula grátis (preview) com o id do vídeo — exposto SÓ para aulas gratuitas."""
    id: uuid.UUID
    titulo: str
    panda_video_id: str | None = None


class ModuloDetalhe(BaseModel):
    id: uuid.UUID
    titulo: str
    ordem: int
    total_aulas: int
    aulas: list[AulaResumo]


class CursoDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    titulo: str
    descricao: str | None = None
    tipo: TipoCurso
    preco: float
    preco_antigo: float | None = None
    validade_dias: int
    thumbnail_url: str | None = None
    gratuito: bool = False  # curso 100% grátis (matrícula free)
    # marketing / vitrine
    tagline: str | None = None
    horas: str | None = None
    aulas_total: int = 0
    rating: float | None = None
    alunos: int = 0
    nivel: str | None = None
    icon: str | None = None
    badge_label: str | None = None
    aprende: list[str] = []
    modulos: list[ModuloDetalhe]
    # Avaliações reais dos alunos (alimentam aggregateRating no JSON-LD).
    rating_medio: float | None = None
    rating_count: int = 0
