import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import PapelAdmin, TipoCurso

# Domínios fechados de status (validados no boundary; evita valor fora do conjunto
# que sumiria silenciosamente da filtragem pública por igualdade exata).
StatusAprovacao = Literal["Aprovado", "Pendente"]
StatusAtivo = Literal["Ativo", "Inativo"]
# Senha: max 72 (limite efetivo do bcrypt) / min 8.
_SENHA = Field(min_length=8, max_length=72)


def _so_http_url(v: str | None) -> str | None:
    """Aceita só http(s):// — barra esquemas executáveis (javascript:, data:,
    vbscript:) que viram XSS quando a URL é renderizada em href no portal."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if not v.lower().startswith(("http://", "https://")):
        raise ValueError("URL deve começar com http:// ou https://")
    return v


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
    tagline: str | None = Field(default=None, max_length=300)
    descricao: str | None = Field(default=None, max_length=5000)
    tipo: TipoCurso = TipoCurso.avulso
    preco: float = Field(default=0, ge=0)  # nunca negativo (vai pro Stripe/banco)
    preco_antigo: float | None = Field(default=None, ge=0)
    horas: str | None = Field(default=None, max_length=20)
    aulas_total: int = Field(default=0, ge=0)
    rating: float | None = Field(default=None, ge=0, le=9.9)  # Numeric(2,1)
    alunos: int = Field(default=0, ge=0)
    nivel: str | None = Field(default=None, max_length=40)
    icon: str | None = Field(default=None, max_length=40)
    badge_label: str | None = Field(default=None, max_length=40)
    validade_dias: int = Field(default=365, gt=0)
    destaque: bool = False
    ordem: int = Field(default=0, ge=0)
    thumbnail_url: str | None = Field(default=None, max_length=500)


class CursoUpdate(BaseModel):
    slug: str | None = None
    titulo: str | None = None
    tagline: str | None = Field(default=None, max_length=300)
    descricao: str | None = Field(default=None, max_length=5000)
    tipo: TipoCurso | None = None
    preco: float | None = Field(default=None, ge=0)
    preco_antigo: float | None = Field(default=None, ge=0)
    horas: str | None = Field(default=None, max_length=20)
    aulas_total: int | None = Field(default=None, ge=0)
    rating: float | None = Field(default=None, ge=0, le=9.9)
    alunos: int | None = Field(default=None, ge=0)
    nivel: str | None = Field(default=None, max_length=40)
    icon: str | None = Field(default=None, max_length=40)
    badge_label: str | None = Field(default=None, max_length=40)
    validade_dias: int | None = Field(default=None, gt=0)
    destaque: bool | None = None
    ordem: int | None = Field(default=None, ge=0)
    thumbnail_url: str | None = Field(default=None, max_length=500)


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
    papel: str | None = Field(default=None, max_length=160)
    estrelas: int = Field(default=5, ge=1, le=5)
    texto: str = Field(min_length=2, max_length=5000)
    status: StatusAprovacao = "Pendente"
    ordem: int = 0


class DepoimentoUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=160)
    papel: str | None = Field(default=None, max_length=160)
    estrelas: int | None = Field(default=None, ge=1, le=5)
    texto: str | None = Field(default=None, max_length=5000)
    status: StatusAprovacao | None = None
    ordem: int | None = None


# ── Planos de assinatura (Premium — acesso ao catálogo inteiro) ───────────────
class PlanoAssinaturaAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    intervalo: str
    stripe_price_id: str
    preco: float
    status: str
    ordem: int


class PlanoAssinaturaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    intervalo: Literal["mensal", "anual"] = "anual"
    # Price RECORRENTE do Stripe (price_...). Vazio + Stripe configurado → o
    # backend cria Product+Price automaticamente a partir de nome/intervalo/preco.
    stripe_price_id: str = Field(default="", max_length=255)
    preco: float = Field(default=0, ge=0)
    status: StatusAtivo = "Ativo"
    ordem: int = Field(default=0, ge=0)


class PlanoAssinaturaUpdate(BaseModel):
    # SEM stripe_price_id: o id é gerido exclusivamente pelo backend (sync com a
    # Stripe). Aceitá-lo em update corrompe — o form ecoa o objeto inteiro e um
    # valor desatualizado apontaria o plano p/ um Price inativo/errado.
    nome: str | None = Field(default=None, max_length=120)
    intervalo: Literal["mensal", "anual"] | None = None
    preco: float | None = Field(default=None, ge=0)
    status: StatusAtivo | None = None
    ordem: int | None = Field(default=None, ge=0)


# ── Vídeos (prova social) ─────────────────────────────────────────────────────
class VideoAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    youtube_url: str | None = None
    canal: str | None = None
    duracao: str | None = None
    views: str | None = None
    likes: str | None = None
    estrelas: int
    status: str
    ordem: int


class VideoCreate(BaseModel):
    # título/canal/duração/views/likes opcionais: o backend completa pelo YouTube
    # (Data API se houver chave, senão oEmbed) ao salvar.
    titulo: str = Field(default="", max_length=200)
    youtube_url: str | None = Field(default=None, max_length=500)
    canal: str | None = Field(default=None, max_length=120)
    duracao: str | None = Field(default=None, max_length=20)
    views: str | None = Field(default=None, max_length=40)
    likes: str | None = Field(default=None, max_length=40)
    estrelas: int = Field(default=5, ge=1, le=5)
    status: StatusAtivo = "Ativo"
    ordem: int = 0

    _valida_url = field_validator("youtube_url")(_so_http_url)


class VideoUpdate(BaseModel):
    titulo: str | None = Field(default=None, max_length=200)
    youtube_url: str | None = Field(default=None, max_length=500)
    canal: str | None = Field(default=None, max_length=120)
    duracao: str | None = Field(default=None, max_length=20)
    views: str | None = Field(default=None, max_length=40)
    likes: str | None = Field(default=None, max_length=40)
    estrelas: int | None = Field(default=None, ge=1, le=5)
    status: StatusAtivo | None = None
    ordem: int | None = None

    _valida_url = field_validator("youtube_url")(_so_http_url)


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
    resposta: str = Field(min_length=2, max_length=5000)
    status: StatusAtivo = "Ativo"
    ordem: int = 0


class FaqUpdate(BaseModel):
    pergunta: str | None = Field(default=None, max_length=300)
    resposta: str | None = Field(default=None, max_length=5000)
    status: StatusAtivo | None = None
    ordem: int | None = None


# ── Avaliações dos alunos (moderação) ─────────────────────────────────────────
class AvaliacaoAdminItem(BaseModel):
    id: uuid.UUID
    aluno_nome: str
    curso_titulo: str
    nota: int
    texto: str | None
    status: str
    criado_em: datetime


class AvaliacaoStatusUpdate(BaseModel):
    status: StatusAprovacao  # "Aprovado" | "Pendente"


# ── Reembolsos (cancelamento pelo suporte) ────────────────────────────────────
class ReembolsoItem(BaseModel):
    matricula_id: uuid.UUID
    curso_titulo: str
    status: str
    origem: str  # avulsa | assinatura | manual
    valor: float | None = None
    pago_em: datetime | None = None
    dentro_da_janela: bool  # janela de 7 dias do aluno (informativo p/ o suporte)
    cancelavel: bool


class AlunoReembolsos(BaseModel):
    aluno_id: uuid.UUID
    nome: str
    email: str
    matriculas: list[ReembolsoItem]


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
    senha: str = _SENHA
    papel: PapelAdmin = PapelAdmin.suporte
    ativo: bool = True


class AdminUserUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    senha: str | None = Field(default=None, min_length=8, max_length=72)
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
    senha: str = _SENHA
    telefone: str | None = Field(default=None, max_length=40)


class AlunoUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    senha: str | None = Field(default=None, min_length=8, max_length=72)
    telefone: str | None = Field(default=None, max_length=40)
