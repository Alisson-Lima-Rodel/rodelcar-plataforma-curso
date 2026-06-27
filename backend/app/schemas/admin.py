import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import PapelAdmin, StatusCurso, TipoCurso

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


def _url_http_obrigatoria(v: str | None) -> str:
    """Como _so_http_url, mas OBRIGATÓRIA: recusa None/vazio (não deixa gravar URL
    nula numa coluna NOT NULL → 422 em vez de estourar IntegrityError/500). Para a
    foto de turma, cuja URL sempre vem do upload. No update só roda quando o campo
    é enviado (validate_default desligado), então omitir a url continua permitido."""
    if v is None or not v.strip():
        raise ValueError("URL é obrigatória.")
    v = v.strip()
    if not v.lower().startswith(("http://", "https://")):
        raise ValueError("URL deve começar com http:// ou https://")
    return v


# Telefone BR (DDD + número): validador compartilhado com o cadastro público.
from app.core.validators import telefone_br as _telefone_br


# ── Auth do painel ────────────────────────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    email: EmailStr
    senha: str


class AdminTokenResponse(BaseModel):
    access_token: str
    # Refresh do painel: renova o access sem novo login (sessão dura mais que os
    # 30 min do access). Revogado em lote pelo logout (bump de token_version).
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminRefreshRequest(BaseModel):
    refresh_token: str


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
    rating: float | None = None
    nivel: str | None = None
    icon: str | None = None
    badge_label: str | None = None
    validade_dias: int
    destaque: bool
    gratuito: bool
    status: StatusCurso
    ordem: int
    thumbnail_url: str | None = None
    idiomas_legenda: list[str] = []
    # Contagens CALCULADAS do conteúdo cadastrado (read-only; o admin não digita
    # mais). Preenchidas pelo router ao montar a resposta (não vêm do ORM).
    total_modulos: int = 0
    total_aulas: int = 0
    horas: str | None = None  # tempo total de vídeo, ex.: "8h40"


class CursoCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120)
    titulo: str = Field(min_length=2, max_length=200)
    tagline: str | None = Field(default=None, max_length=300)
    descricao: str | None = Field(default=None, max_length=5000)
    tipo: TipoCurso = TipoCurso.avulso
    preco: float = Field(default=0, ge=0)  # nunca negativo (vai pro Stripe/banco)
    preco_antigo: float | None = Field(default=None, ge=0)
    rating: float | None = Field(default=None, ge=0, le=9.9)  # Numeric(2,1)
    nivel: str | None = Field(default=None, max_length=40)
    icon: str | None = Field(default=None, max_length=40)
    badge_label: str | None = Field(default=None, max_length=40)
    validade_dias: int = Field(default=365, gt=0)
    destaque: bool = False
    gratuito: bool = False
    ordem: int = Field(default=0, ge=0)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    idiomas_legenda: list[str] = Field(default_factory=list)
    # `status` NÃO é aceito na criação: todo curso nasce "em_desenvolvimento"
    # (forçado no router). `aulas_total`/`horas` são calculados; `alunos` foi removido.


class CursoUpdate(BaseModel):
    slug: str | None = None
    titulo: str | None = None
    tagline: str | None = Field(default=None, max_length=300)
    descricao: str | None = Field(default=None, max_length=5000)
    tipo: TipoCurso | None = None
    preco: float | None = Field(default=None, ge=0)
    preco_antigo: float | None = Field(default=None, ge=0)
    rating: float | None = Field(default=None, ge=0, le=9.9)
    nivel: str | None = Field(default=None, max_length=40)
    icon: str | None = Field(default=None, max_length=40)
    badge_label: str | None = Field(default=None, max_length=40)
    validade_dias: int | None = Field(default=None, gt=0)
    destaque: bool | None = None
    gratuito: bool | None = None
    status: StatusCurso | None = None
    ordem: int | None = Field(default=None, ge=0)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    idiomas_legenda: list[str] | None = None


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


# ── Mídia de turmas presenciais (mosaico bento da home) ───────────────────────
class TurmaMidiaAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    alt: str | None = None
    destaque: bool
    status: str
    ordem: int


class TurmaMidiaCreate(BaseModel):
    url: str = Field(max_length=500)
    alt: str | None = Field(default=None, max_length=300)
    destaque: bool = False
    status: StatusAtivo = "Ativo"
    ordem: int = 0

    _valida_url = field_validator("url")(_url_http_obrigatoria)


class TurmaMidiaUpdate(BaseModel):
    # url é opcional p/ OMITIR (edita só alt/ordem/status), mas se enviada não
    # pode ser nula/vazia — a coluna é NOT NULL. _url_http_obrigatoria garante 422.
    url: str | None = Field(default=None, max_length=500)
    alt: str | None = Field(default=None, max_length=300)
    destaque: bool | None = None
    status: StatusAtivo | None = None
    ordem: int | None = None

    _valida_url = field_validator("url")(_url_http_obrigatoria)


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


# ── Cupons de desconto (Stripe Coupon + Promotion Code) ───────────────────────
class CupomAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    descricao: str | None = None
    tipo: str
    valor: float
    ativo: bool
    max_resgates: int | None = None
    validade: datetime | None = None
    criado_em: datetime


class CupomCreate(BaseModel):
    codigo: str = Field(min_length=3, max_length=40)
    descricao: str | None = Field(default=None, max_length=200)
    tipo: Literal["percentual", "valor"] = "percentual"
    valor: float = Field(gt=0)  # % (1-100) ou R$
    max_resgates: int | None = Field(default=None, ge=0)  # 0/None = ilimitado
    validade: datetime | None = None

    @field_validator("codigo")
    @classmethod
    def _codigo_limpo(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Código só pode ter letras, números, '-' e '_'.")
        return v

    @field_validator("valor")
    @classmethod
    def _valor_ok(cls, v: float, info) -> float:
        # Stripe rejeita percent_off < 1; barra aqui (422) em vez de 502 depois.
        if info.data.get("tipo") == "percentual" and not (1 <= v <= 100):
            raise ValueError("Percentual deve estar entre 1 e 100.")
        return v


class CupomUpdate(BaseModel):
    # Desconto/código são IMUTÁVEIS na Stripe — só descrição e ativo mudam.
    descricao: str | None = Field(default=None, max_length=200)
    ativo: bool | None = None


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
    bloqueado: bool = False
    # "Bloqueado" (trava manual) tem prioridade; senão "Ativo"/"Inativo" da matrícula.
    status: str = "Inativo"


class AlunoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = _SENHA
    telefone: str | None = Field(default=None, max_length=40)

    _valida_tel = field_validator("telefone")(_telefone_br)


class AlunoUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    senha: str | None = Field(default=None, min_length=8, max_length=72)
    telefone: str | None = Field(default=None, max_length=40)

    _valida_tel = field_validator("telefone")(_telefone_br)


class AlunoBloqueioUpdate(BaseModel):
    bloqueado: bool


class RecuperarSenhaResponse(BaseModel):
    """Token bruto devolvido UMA vez ao admin p/ montar o link de redefinição."""
    token: str
    expira_em: datetime


# ── Matrículas (gestão de acesso / reembolso) ─────────────────────────────────
class MatriculaAdminItem(BaseModel):
    matricula_id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str
    aluno_email: str
    aluno_telefone: str | None = None
    aluno_bloqueado: bool
    curso_titulo: str
    origem: str  # avulsa | assinatura | manual
    status: str  # ativo | expirado | bloqueado
    valor: float | None = None
    pago_em: datetime | None = None
    dentro_da_janela: bool
    cancelavel: bool


# ── Métricas diárias (visão geral) ────────────────────────────────────────────
class MetricaDiaria(BaseModel):
    dia: date
    acessos: int
    aulas_assistidas: int
    compras: int
