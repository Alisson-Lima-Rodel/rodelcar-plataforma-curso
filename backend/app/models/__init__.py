from __future__ import annotations

import enum
import os
import uuid
from datetime import datetime
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
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
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Chave Fernet ausente/rotacionada fora de ordem: NÃO propaga (a coluna
            # é lida em todo SELECT do Aluno → estouraria 500 em cada request
            # autenticada = DoS de autenticação). Loga e devolve None.
            import logging
            logging.getLogger(__name__).error(
                "Falha ao decifrar campo cifrado (RODELCAR_FERNET_KEY ausente/"
                "rotacionada?). Verifique as chaves Fernet."
            )
            return None


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


class StatusCurso(str, enum.Enum):
    # Rascunho: visível só no admin, não vende. Todo curso nasce aqui.
    em_desenvolvimento = "em_desenvolvimento"
    # Publicado: aparece na vitrine pública e na página de venda (vende).
    ativo = "ativo"
    # Arquivado: some do site, mas NÃO corta quem já comprou (acesso é barrado por
    # status de matrícula, não pela vitrine).
    inativo = "inativo"


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
    # Acesso bloqueado manualmente pelo admin: recusa login E derruba sessões vivas
    # (ao bloquear, o token_version é incrementado). Difere de matrícula expirada
    # (vigência): é uma trava independente de ter cursos ativos.
    bloqueado: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # Customer do Stripe (cus_...); criado no 1º checkout e reaproveitado depois.
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    # Código pessoal do indique-e-ganhe (gerado no cadastro; lazy p/ contas antigas).
    codigo_indicacao: Mapped[str | None] = mapped_column(
        String(20), unique=True, index=True
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


class AdminRefreshToken(Base):
    """Refresh tokens do painel admin — STATEFUL, espelha RefreshToken do aluno.

    Mesma regra segura: rotação no refresh e detecção de reuso. Apresentar um
    token já revogado indica reuso/roubo → revoga toda a família do admin e
    incrementa `Admin.token_version` (mata também os access vivos).
    """
    __tablename__ = "admin_refresh_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), index=True
    )
    jti: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogado: Mapped[bool] = mapped_column(Boolean, default=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = _created_at()


class PasswordReset(Base):
    """Token de redefinição de senha do aluno (single-use, gerado pelo admin).

    O admin dispara a recuperação; o backend gera um token aleatório, guarda só o
    SHA-256 dele (nunca o bruto) e devolve o bruto UMA vez para o admin montar o
    link e enviar por WhatsApp/e-mail. O aluno abre o link, define a senha nova e a
    linha é marcada como usada. Expira em 24h.
    """
    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
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
    # Idiomas de legenda disponíveis (ex.: ["PT","EN","ES"]) — só metadado de
    # vitrine p/ o selo "Legendado em…" na página de venda. A legenda em si é
    # gerada/renderizada pelo Panda (legenda IA no dashboard).
    idiomas_legenda: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    # Curso 100% gratuito: o aluno cadastrado se matricula de graça (sem Stripe) e
    # acessa todas as aulas. Ímã de leads. Difere de Aula.gratuita (amostra avulsa).
    gratuito: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # Estado de publicação (3 fases). Nasce `em_desenvolvimento` (rascunho); só
    # `ativo` aparece na vitrine/página de venda e pode ser comprado; `inativo`
    # some do site, mas NÃO corta quem já comprou (barrado por status de matrícula).
    # Só vai para `ativo` se houver conteúdo cadastrado (regra no router).
    status: Mapped[StatusCurso] = mapped_column(
        Enum(StatusCurso, name="statuscurso"),
        default=StatusCurso.em_desenvolvimento,
        server_default=StatusCurso.em_desenvolvimento.value,
    )

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
    # Id do EMBED (video_external_id do Panda) — vai no ?v= do player. DIFERE do
    # panda_video_id (id da REST API, usado em sync/retenção). Sem ele, o player
    # embeda o id errado e mostra falha. Preenchido no sync/lazy a partir da API.
    panda_external_id: Mapped[str | None] = mapped_column(String(120))
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
    # Último segundo assistido — usado para dar `seek` ao reabrir (resume
    # cross-device). Difere de `percentual` (ponto mais distante / progresso).
    posicao_segundos: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    # Tempo REAL assistido, acumulado pelo servidor (delta de relógio entre pings,
    # limitado por ping). Gate anti-fraude do certificado: 100% instantâneo acumula
    # ~0s e não conta. Cliente NUNCA envia este valor.
    segundos_assistidos: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
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
    # SET NULL: excluir um aluno NÃO apaga o histórico de eventos (as métricas
    # diárias contam por dia, independem do aluno), e o delete não viola a FK.
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alunos.id", ondelete="SET NULL")
    )
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
    # Vídeo saiu do ar no YouTube (apagado/privado), detectado pelo job diário.
    # Some da capa sem o admin precisar agir; volta sozinho se o vídeo reaparecer.
    # Separado de `status` (intenção do admin) p/ não sobrescrever a curadoria.
    indisponivel: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
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


class Cupom(Base):
    """Cupom de desconto. Espelha um Coupon + Promotion Code da Stripe: o cliente
    digita o `codigo` na tela hospedada do Checkout (allow_promotion_codes). O
    desconto (% ou R$) é IMUTÁVEL na Stripe — editar troca só `ativo`/descrição.
    Também é a recompensa do indique-e-ganhe (gerado por aluno).
    """
    __tablename__ = "cupons"

    id: Mapped[uuid.UUID] = _uuid_pk()
    codigo: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    descricao: Mapped[str | None] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(20))  # percentual | valor
    valor: Mapped[float] = mapped_column(Numeric(10, 2))  # 20 (%) ou 50.00 (R$)
    stripe_coupon_id: Mapped[str | None] = mapped_column(String(255))
    stripe_promotion_code_id: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    max_resgates: Mapped[int | None] = mapped_column(Integer)
    validade: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Origem: NULL = criado pelo admin; senão o aluno que ganhou (referral).
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alunos.id", ondelete="SET NULL"), index=True
    )
    criado_em: Mapped[datetime] = _created_at()


class Indicacao(Base):
    """Indique-e-ganhe: liga o indicador (dono do código) ao indicado (quem se
    cadastrou com ele). Quando o indicado faz a 1ª compra confirmada, AMBOS ganham
    um cupom. 1 atribuição por indicado (não dá p/ ser indicado duas vezes).

    Estados: pendente → compra_confirmada (webhook) → recompensado (cupons gerados).
    """
    __tablename__ = "indicacoes"
    __table_args__ = (
        UniqueConstraint("indicado_id", name="uq_indicacao_indicado"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    indicador_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), index=True
    )
    indicado_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pendente", server_default="pendente"
    )
    cupom_indicador_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cupons.id", ondelete="SET NULL")
    )
    cupom_indicado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cupons.id", ondelete="SET NULL")
    )
    criado_em: Mapped[datetime] = _created_at()
    recompensado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Quiz(Base):
    """Prova de um módulo. Para emitir o certificado, o aluno precisa assistir as
    aulas E passar (nota >= nota_corte) nos quizzes ATIVOS de cada módulo do curso.
    1 quiz por módulo.
    """
    __tablename__ = "quizzes"
    __table_args__ = (UniqueConstraint("modulo_id", name="uq_quiz_modulo"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    modulo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modulos.id", ondelete="CASCADE"), index=True
    )
    titulo: Mapped[str] = mapped_column(String(200))
    nota_corte: Mapped[float] = mapped_column(
        Numeric(5, 2), default=70, server_default="70"
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    criado_em: Mapped[datetime] = _created_at()

    questoes: Mapped[list[Questao]] = relationship(
        back_populates="quiz", order_by="Questao.ordem", cascade="all, delete-orphan"
    )


class Questao(Base):
    __tablename__ = "questoes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), index=True
    )
    enunciado: Mapped[str] = mapped_column(Text())
    ordem: Mapped[int] = mapped_column(Integer, default=0)

    quiz: Mapped[Quiz] = relationship(back_populates="questoes")
    alternativas: Mapped[list[Alternativa]] = relationship(
        back_populates="questao",
        order_by="Alternativa.ordem",
        cascade="all, delete-orphan",
    )


class Alternativa(Base):
    __tablename__ = "alternativas"

    id: Mapped[uuid.UUID] = _uuid_pk()
    questao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questoes.id", ondelete="CASCADE"), index=True
    )
    texto: Mapped[str] = mapped_column(String(500))
    correta: Mapped[bool] = mapped_column(Boolean, default=False)
    ordem: Mapped[int] = mapped_column(Integer, default=0)

    questao: Mapped[Questao] = relationship(back_populates="alternativas")


class TentativaQuiz(Base):
    """Tentativa de um quiz por uma matrícula. Guarda o histórico; o gate do
    certificado olha se HÁ ao menos uma tentativa aprovada por (matrícula, quiz)."""
    __tablename__ = "tentativas_quiz"

    id: Mapped[uuid.UUID] = _uuid_pk()
    matricula_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matriculas.id", ondelete="CASCADE"), index=True
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), index=True
    )
    nota: Mapped[float] = mapped_column(Numeric(5, 2))
    aprovado: Mapped[bool] = mapped_column(Boolean, default=False)
    respostas: Mapped[dict] = mapped_column(JSONB, default=dict)
    criado_em: Mapped[datetime] = _created_at()


class TurmaMidia(Base):
    """Foto de turma presencial no mosaico bento da home (seção "Turmas
    presenciais"). Gerenciada pelo admin (upload + reordenar + ativar), sem deploy.
    O vídeo em destaque da seção é um asset estático em public/; aqui só o mosaico.
    """
    __tablename__ = "turmas_midia"

    id: Mapped[uuid.UUID] = _uuid_pk()
    url: Mapped[str] = mapped_column(String(500))
    # Texto alternativo: acessibilidade + legenda no lightbox.
    alt: Mapped[str | None] = mapped_column(String(300))
    # Destaque: tile grande (bento-wide) no mosaico; senão tile alto (bento-tall).
    destaque: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    # Ativo/Inativo (string p/ casar com o CRUD genérico e o filtro do admin,
    # igual a Video/Faq). O endpoint público só expõe os "Ativo".
    status: Mapped[str] = mapped_column(
        String(20), default="Ativo", server_default="Ativo"
    )
    criado_em: Mapped[datetime] = _created_at()
