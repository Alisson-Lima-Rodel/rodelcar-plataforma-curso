from __future__ import annotations

import enum
import os
import uuid
from datetime import datetime
from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, Integer,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


@lru_cache(maxsize=1)
def _get_fernet() -> MultiFernet:
    """MultiFernet para permitir ROTAÇÃO de chave sem perder CPFs já cifrados.

    Cifra sempre com a 1ª chave (primária); decifra tentando todas. Para rotacionar:
    gere uma nova chave, coloque-a em `RODELCAR_FERNET_KEY` e mova a antiga para
    `RODELCAR_FERNET_KEYS` (lista por vírgula). Dados antigos continuam legíveis e
    novos registros usam a chave nova; depois de recifrar tudo, remova a antiga.
    """
    primary = os.environ.get("RODELCAR_FERNET_KEY", "")
    extras = os.environ.get("RODELCAR_FERNET_KEYS", "")
    raw = [k.strip() for k in [primary, *extras.split(",")] if k.strip()]
    if not raw:
        raise RuntimeError("RODELCAR_FERNET_KEY environment variable is required")
    return MultiFernet([Fernet(k.encode()) for k in raw])


class EncryptedStr(TypeDecorator):
    """Cifra/decifra strings com Fernet de forma transparente (CPF — LGPD)."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _get_fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _get_fernet().decrypt(value.encode()).decode()


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class TipoCurso(str, enum.Enum):
    avulso = "avulso"
    premium = "premium"


class StatusMatricula(str, enum.Enum):
    ativo = "ativo"
    expirado = "expirado"
    bloqueado = "bloqueado"


class StatusPagamento(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    recusado = "recusado"
    estornado = "estornado"


class StatusLead(str, enum.Enum):
    novo = "novo"
    contatado = "contatado"
    agendado = "agendado"
    concluido = "concluido"
    perdido = "perdido"


class StatusCarro(str, enum.Enum):
    disponivel = "disponivel"
    reservado = "reservado"
    vendido = "vendido"


class CanalNotificacao(str, enum.Enum):
    email = "email"
    whatsapp = "whatsapp"


class TipoNotificacao(str, enum.Enum):
    vigencia_proxima = "vigencia_proxima"
    vigencia_expirada = "vigencia_expirada"
    promo_renovacao = "promo_renovacao"


class StatusNotificacao(str, enum.Enum):
    pendente = "pendente"
    enviada = "enviada"
    falhou = "falhou"


class PapelAdmin(str, enum.Enum):
    administrador = "Administrador"
    editor = "Editor"
    suporte = "Suporte"


# --------------------------------------------------------------------------- #
# Entidades
# --------------------------------------------------------------------------- #
class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    cpf: Mapped[str | None] = mapped_column(EncryptedStr(255))
    telefone: Mapped[str | None] = mapped_column(String(40))
    senha_hash: Mapped[str] = mapped_column(String(255))
    # Versão da sessão: embutida no access token (claim "tv") e conferida a cada
    # request. Incrementar invalida TODOS os access tokens vivos do aluno (ex.: ao
    # detectar reuso de refresh = roubo). Default 0 mantém tokens antigos válidos.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Customer do Stripe (cus_...); criado no 1º checkout e reaproveitado depois.
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    criado_em: Mapped[datetime] = _created_at()

    matriculas: Mapped[list[Matricula]] = relationship(back_populates="aluno")
    pagamentos: Mapped[list[Pagamento]] = relationship(back_populates="aluno")


class RefreshToken(Base):
    """Refresh tokens emitidos, p/ rotação e revogação.

    Cada refresh JWT carrega um `jti` que aponta para uma linha aqui. No refresh,
    o token atual é revogado e um novo é emitido (rotação). Apresentar um token
    já revogado indica reuso/roubo → revoga toda a família do aluno.
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), index=True
    )
    jti: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogado: Mapped[bool] = mapped_column(Boolean, default=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = _created_at()


class Curso(Base):
    __tablename__ = "cursos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text())
    tipo: Mapped[TipoCurso] = mapped_column(Enum(TipoCurso))
    preco: Mapped[float] = mapped_column(Numeric(10, 2))
    validade_dias: Mapped[int] = mapped_column(Integer, default=365)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    destaque: Mapped[bool] = mapped_column(Boolean, default=False)
    # Price do Stripe (price_...) p/ a compra avulsa (one-time). Criado uma vez
    # no Dashboard/script e referenciado aqui — não fixar valor no checkout.
    stripe_price_id: Mapped[str | None] = mapped_column(String(255))

    # ── Campos de marketing/vitrine (página de venda) ──────────────────────────
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    tagline: Mapped[str | None] = mapped_column(String(300))
    preco_antigo: Mapped[float | None] = mapped_column(Numeric(10, 2))
    horas: Mapped[str | None] = mapped_column(String(20))
    aulas_total: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1))
    alunos: Mapped[int] = mapped_column(Integer, default=0)
    nivel: Mapped[str | None] = mapped_column(String(40))
    icon: Mapped[str | None] = mapped_column(String(40))
    badge_label: Mapped[str | None] = mapped_column(String(40))
    aprende: Mapped[list] = mapped_column(JSONB, default=list)

    modulos: Mapped[list[Modulo]] = relationship(
        back_populates="curso", order_by="Modulo.ordem"
    )


class Modulo(Base):
    __tablename__ = "modulos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    curso_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cursos.id"))
    titulo: Mapped[str] = mapped_column(String(200))
    ordem: Mapped[int] = mapped_column(Integer, default=0)

    curso: Mapped[Curso] = relationship(back_populates="modulos")
    aulas: Mapped[list[Aula]] = relationship(
        back_populates="modulo", order_by="Aula.ordem"
    )


class Aula(Base):
    __tablename__ = "aulas"

    id: Mapped[uuid.UUID] = _uuid_pk()
    modulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modulos.id"))
    titulo: Mapped[str] = mapped_column(String(200))
    panda_video_id: Mapped[str | None] = mapped_column(String(120))
    duracao_segundos: Mapped[int] = mapped_column(Integer, default=0)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    # Aula liberada como amostra (preview) na página de venda, sem compra. O vídeo
    # dela é exposto por um endpoint público; as demais NUNCA vazam.
    gratuita: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    modulo: Mapped[Modulo] = relationship(back_populates="aulas")
    materiais: Mapped[list[MaterialApoio]] = relationship(back_populates="aula")


class MaterialApoio(Base):
    __tablename__ = "materiais_apoio"

    id: Mapped[uuid.UUID] = _uuid_pk()
    aula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aulas.id"))
    nome: Mapped[str] = mapped_column(String(200))
    url_pdf: Mapped[str] = mapped_column(String(500))

    aula: Mapped[Aula] = relationship(back_populates="materiais")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alunos.id"))
    gateway: Mapped[str] = mapped_column(String(40))
    gateway_transaction_id: Mapped[str] = mapped_column(
        String(120), unique=True, index=True
    )
    valor: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[StatusPagamento] = mapped_column(Enum(StatusPagamento))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    criado_em: Mapped[datetime] = _created_at()

    aluno: Mapped[Aluno | None] = relationship(back_populates="pagamentos")


class Matricula(Base):
    __tablename__ = "matriculas"
    __table_args__ = (UniqueConstraint("aluno_id", "curso_id", name="uq_aluno_curso"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alunos.id"))
    curso_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cursos.id"))
    pagamento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pagamentos.id"))
    # Assinatura do Stripe (sub_...) que concede esta matrícula. Permite renovar
    # (invoice.paid) e revogar (customer.subscription.deleted) em lote.
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[StatusMatricula] = mapped_column(
        Enum(StatusMatricula), default=StatusMatricula.ativo
    )
    data_inicio: Mapped[datetime] = _created_at()
    data_expiracao: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    aluno: Mapped[Aluno] = relationship(back_populates="matriculas")
    curso: Mapped[Curso] = relationship()
    progresso: Mapped[list[Progresso]] = relationship(back_populates="matricula")
    certificado: Mapped[Certificado | None] = relationship(back_populates="matricula")


class Progresso(Base):
    __tablename__ = "progresso"
    __table_args__ = (
        UniqueConstraint("matricula_id", "aula_id", name="uq_matricula_aula"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matriculas.id"))
    aula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aulas.id"))
    concluida: Mapped[bool] = mapped_column(Boolean, default=False)
    percentual: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    matricula: Mapped[Matricula] = relationship(back_populates="progresso")


class Certificado(Base):
    __tablename__ = "certificados"

    id: Mapped[uuid.UUID] = _uuid_pk()
    matricula_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matriculas.id"), unique=True
    )
    codigo_verificacao: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    emitido_em: Mapped[datetime] = _created_at()

    matricula: Mapped[Matricula] = relationship(back_populates="certificado")


class Avaliacao(Base):
    """Review de um curso por um aluno matriculado (comprador verificado).

    Vira `aggregateRating` no JSON-LD (estrelas no Google) e prova social na
    página de venda. Difere de `Depoimento` (curado, sem vínculo a aluno/curso):
    aqui é avaliação de quem comprou. 1 por (aluno, curso) — reenviar atualiza.
    """
    __tablename__ = "avaliacoes"
    __table_args__ = (
        UniqueConstraint("aluno_id", "curso_id", name="uq_avaliacao_aluno_curso"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), index=True
    )
    curso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cursos.id", ondelete="CASCADE"), index=True
    )
    nota: Mapped[int] = mapped_column(Integer)  # 1..5
    texto: Mapped[str | None] = mapped_column(Text())
    # Comprador verificado publica direto; o admin pode ocultar (Pendente/Aprovado).
    status: Mapped[str] = mapped_column(String(20), default="Aprovado")
    criado_em: Mapped[datetime] = _created_at()


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(160))
    telefone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(255))
    tipo_servico: Mapped[str] = mapped_column(String(80))
    mensagem: Mapped[str | None] = mapped_column(Text())
    origem: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[StatusLead] = mapped_column(Enum(StatusLead), default=StatusLead.novo)
    criado_em: Mapped[datetime] = _created_at()


class EstoqueCarro(Base):
    __tablename__ = "estoque_carros"

    id: Mapped[uuid.UUID] = _uuid_pk()
    modelo: Mapped[str] = mapped_column(String(160))
    ano: Mapped[int] = mapped_column(Integer)
    preco: Mapped[float] = mapped_column(Numeric(12, 2))
    descricao: Mapped[str | None] = mapped_column(Text())
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[StatusCarro] = mapped_column(
        Enum(StatusCarro), default=StatusCarro.disponivel
    )
    criado_em: Mapped[datetime] = _created_at()


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alunos.id"))
    nome_evento: Mapped[str] = mapped_column(String(120), index=True)
    sessao_id: Mapped[str | None] = mapped_column(String(80), index=True)
    propriedades: Mapped[dict] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = _created_at()


class Notificacao(Base):
    """Log de vigência/renovação. Idempotência por (matricula_id, tipo, canal, marco)."""
    __tablename__ = "notificacoes"
    __table_args__ = (
        UniqueConstraint(
            "matricula_id", "tipo", "canal", "marco",
            name="uq_notificacao_marco",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alunos.id"))
    matricula_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matriculas.id"))
    canal: Mapped[CanalNotificacao] = mapped_column(Enum(CanalNotificacao))
    tipo: Mapped[TipoNotificacao] = mapped_column(Enum(TipoNotificacao))
    marco: Mapped[str] = mapped_column(String(20))
    status: Mapped[StatusNotificacao] = mapped_column(
        Enum(StatusNotificacao), default=StatusNotificacao.pendente
    )
    provedor_msg_id: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    criado_em: Mapped[datetime] = _created_at()
    enviada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Admin(Base):
    """Usuário do painel administrador (equipe da Rödelcar). Separado de Aluno."""
    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    # Versão da sessão (claim "tv"): o admin não tem refresh, então o logout
    # incrementa este contador para invalidar o(s) access token(s) vivos.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    papel: Mapped[PapelAdmin] = mapped_column(
        # values_callable: o tipo Postgres usa os VALORES ("Administrador"…),
        # não os nomes dos membros — casa com o enum criado na migração.
        Enum(PapelAdmin, name="papeladmin", values_callable=lambda e: [m.value for m in e]),
        default=PapelAdmin.suporte,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = _created_at()


class Depoimento(Base):
    """Depoimento de aluno exibido na prova social (após aprovação)."""
    __tablename__ = "depoimentos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(160))
    papel: Mapped[str | None] = mapped_column(String(160))
    estrelas: Mapped[int] = mapped_column(Integer, default=5)
    texto: Mapped[str] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(20), default="Pendente")  # Aprovado | Pendente
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = _created_at()


class Video(Base):
    """Vídeo do YouTube exibido na prova social do portal."""
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    titulo: Mapped[str] = mapped_column(String(200))
    youtube_url: Mapped[str | None] = mapped_column(String(500))
    # Canal/autor — extraído do YouTube (oEmbed) no cadastro; editável.
    canal: Mapped[str | None] = mapped_column(String(120))
    duracao: Mapped[str | None] = mapped_column(String(20))
    views: Mapped[str | None] = mapped_column(String(40))
    # Likes do YouTube (via Data API, se houver chave). String formatada ("1,2 mil").
    likes: Mapped[str | None] = mapped_column(String(40))
    # Avaliação curada exibida na prova social (YouTube não expõe nota pública).
    estrelas: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    status: Mapped[str] = mapped_column(String(20), default="Ativo")  # Ativo | Inativo
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = _created_at()


class Faq(Base):
    """Pergunta frequente exibida na página de venda do curso."""
    __tablename__ = "faqs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    pergunta: Mapped[str] = mapped_column(String(300))
    resposta: Mapped[str] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(20), default="Ativo")  # Ativo | Inativo
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = _created_at()


class GoogleReviewCache(Base):
    """Cache (linha única, id=1) da nota/avaliações da ficha do Google.

    Um job diário consulta a Places API e grava aqui; o endpoint público lê
    daqui (sem bater na API a cada visita — cota/custo). Sobrevive a restart e
    a multi-worker (cache em memória não serviria).
    """
    __tablename__ = "google_review_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1))
    total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reviews: Mapped[list] = mapped_column(JSONB, default=list)
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebhookEvento(Base):
    """Log de eventos de webhook já processados (idempotência por event.id).

    O gateway reentrega o mesmo evento em retries; gravar o `event_id` único
    impede reprocessá-lo. Complementa o `gateway_transaction_id` único em
    `Pagamento` (que deduplica eventos DIFERENTES sobre o mesmo pagamento).
    """
    __tablename__ = "webhook_eventos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    gateway: Mapped[str] = mapped_column(String(40))
    tipo: Mapped[str] = mapped_column(String(120))
    processado_em: Mapped[datetime] = _created_at()


class PlanoAssinatura(Base):
    """Plano de assinatura recorrente (acesso total ao catálogo).

    Cada plano referencia um Price recorrente do Stripe (criado uma vez). Cartão e
    Pix Automático usam o MESMO Price — o método é escolhido no checkout.
    """
    __tablename__ = "planos_assinatura"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(120))
    intervalo: Mapped[str] = mapped_column(String(20))  # mensal | anual
    stripe_price_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    preco: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="Ativo")  # Ativo | Inativo
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = _created_at()
