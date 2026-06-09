import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import PapelAdmin, TipoCurso


# ── Auth do painel ────────────────────────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    email: EmailStr
    senha: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    papel: PapelAdmin


# ── Cursos (CRUD) ─────────────────────────────────────────────────────────────
class CursoAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    titulo: str
    tagline: str | None = None
    descricao: str | None = None
    tipo: TipoCurso
    preco: float
    preco_antigo: float | None = None
    horas: str | None = None
    aulas_total: int
    rating: float | None = None
    alunos: int
    nivel: str | None = None
    icon: str | None = None
    badge_label: str | None = None
    validade_dias: int
    destaque: bool
    ordem: int
    thumbnail_url: str | None = None


class CursoCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120)
    titulo: str = Field(min_length=2, max_length=200)
    tagline: str | None = None
    descricao: str | None = None
    tipo: TipoCurso = TipoCurso.avulso
    preco: float = 0
    preco_antigo: float | None = None
    horas: str | None = None
    aulas_total: int = 0
    rating: float | None = None
    alunos: int = 0
    nivel: str | None = None
    icon: str | None = None
    badge_label: str | None = None
    validade_dias: int = 365
    destaque: bool = False
    ordem: int = 0
    thumbnail_url: str | None = None


class CursoUpdate(BaseModel):
    slug: str | None = None
    titulo: str | None = None
    tagline: str | None = None
    descricao: str | None = None
    tipo: TipoCurso | None = None
    preco: float | None = None
    preco_antigo: float | None = None
    horas: str | None = None
    aulas_total: int | None = None
    rating: float | None = None
    alunos: int | None = None
    nivel: str | None = None
    icon: str | None = None
    badge_label: str | None = None
    validade_dias: int | None = None
    destaque: bool | None = None
    ordem: int | None = None
    thumbnail_url: str | None = None


# ── Depoimentos ───────────────────────────────────────────────────────────────
class DepoimentoAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    papel: str | None = None
    estrelas: int
    texto: str
    status: str
    ordem: int


class DepoimentoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    papel: str | None = None
    estrelas: int = Field(default=5, ge=1, le=5)
    texto: str = Field(min_length=2)
    status: str = "Pendente"
    ordem: int = 0


class DepoimentoUpdate(BaseModel):
    nome: str | None = None
    papel: str | None = None
    estrelas: int | None = Field(default=None, ge=1, le=5)
    texto: str | None = None
    status: str | None = None
    ordem: int | None = None


# ── Pacotes ───────────────────────────────────────────────────────────────────
class PacoteAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    preco: float
    preco_antigo: float | None = None
    parcelas: str | None = None
    cursos: int
    inclui: str | None = None
    status: str
    ordem: int


class PacoteCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    preco: float = 0
    preco_antigo: float | None = None
    parcelas: str | None = None
    cursos: int = 1
    inclui: str | None = None
    status: str = "Ativo"
    ordem: int = 0


class PacoteUpdate(BaseModel):
    nome: str | None = None
    preco: float | None = None
    preco_antigo: float | None = None
    parcelas: str | None = None
    cursos: int | None = None
    inclui: str | None = None
    status: str | None = None
    ordem: int | None = None


# ── Vídeos (prova social) ─────────────────────────────────────────────────────
class VideoAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    youtube_url: str | None = None
    duracao: str | None = None
    views: str | None = None
    status: str
    ordem: int


class VideoCreate(BaseModel):
    titulo: str = Field(min_length=2, max_length=200)
    youtube_url: str | None = None
    duracao: str | None = None
    views: str | None = None
    status: str = "Ativo"
    ordem: int = 0


class VideoUpdate(BaseModel):
    titulo: str | None = None
    youtube_url: str | None = None
    duracao: str | None = None
    views: str | None = None
    status: str | None = None
    ordem: int | None = None


# ── FAQ (página de venda) ─────────────────────────────────────────────────────
class FaqAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pergunta: str
    resposta: str
    status: str
    ordem: int


class FaqCreate(BaseModel):
    pergunta: str = Field(min_length=2, max_length=300)
    resposta: str = Field(min_length=2)
    status: str = "Ativo"
    ordem: int = 0


class FaqUpdate(BaseModel):
    pergunta: str | None = None
    resposta: str | None = None
    status: str | None = None
    ordem: int | None = None


# ── Administradores (usuários do painel) ──────────────────────────────────────
class AdminUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    papel: PapelAdmin
    ativo: bool
    ultimo_acesso: datetime | None = None


class AdminUserCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)
    papel: PapelAdmin = PapelAdmin.suporte
    ativo: bool = True


class AdminUserUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    senha: str | None = None
    papel: PapelAdmin | None = None
    ativo: bool | None = None


# ── Alunos (gestão pelo painel) ───────────────────────────────────────────────
# Campos de matrícula (cursos/vigência/status) são derivados e somente-leitura;
# o cadastro edita só os dados reais do aluno. CPF fica fora do painel (LGPD).
class AlunoAdminItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    telefone: str | None = None
    matriculas: int = 0
    vigencia: date | None = None
    status: str = "Inativo"


class AlunoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)
    telefone: str | None = None


class AlunoUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    senha: str | None = None
    telefone: str | None = None
