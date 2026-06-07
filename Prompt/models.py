"""
RödelCar — Modelo de dados (SQLAlchemy 2.0, estilo async/Mapped).

Coloque em backend/app/models/__init__.py (ou divida por domínio).
Requer: sqlalchemy>=2.0, cryptography (Fernet), e uma engine async (asyncpg).

A coluna `cpf` usa o TypeDecorator EncryptedStr: o valor é cifrado com Fernet
antes de ir ao banco e decifrado ao ler. A chave vem de RODELCAR_FERNET_KEY.
"""

from __future__ import annotations

import enum
import os
import uuid
from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, Integer,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
)
from sqlalchemy.types import TypeDecorator


# --------------------------------------------------------------------------- #
# Criptografia de campo (LGPD): CPF cifrado em repouso
# --------------------------------------------------------------------------- #
_fernet = Fernet(os.environ["RODELCAR_FERNET_KEY"].encode())


class EncryptedStr(TypeDecorator):
    """Cifra/decifra strings com Fernet de forma transparente."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return _fernet.decrypt(value.encode()).decode()


# --------------------------------------------------------------------------- #
# Base e mixins
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Entidades
# --------------------------------------------------------------------------- #
class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    cpf: Mapped[str | None] = mapped_column(EncryptedStr(255))  # cifrado (Fernet)
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = _created_at()

    matriculas: Mapped[list[Matricula]] = relationship(back_populates="aluno")
    pagamentos: Mapped[list[Pagamento]] = relationship(back_populates="aluno")


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

    modulo: Mapped[Modulo] = relationship(back_populates="aulas")
    materiais: Mapped[list[MaterialApoio]] = relationship(back_populates="aula")


class MaterialApoio(Base):
    __tablename__ = "materiais_apoio"

    id: Mapped[uuid.UUID] = _uuid_pk()
    aula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aulas.id"))
    nome: Mapped[str] = mapped_column(String(200))
    url_pdf: Mapped[str] = mapped_column(String(500))

    aula: Mapped[Aula] = relationship(back_populates="materiais")


class Matricula(Base):
    __tablename__ = "matriculas"
    __table_args__ = (UniqueConstraint("aluno_id", "curso_id", name="uq_aluno_curso"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alunos.id"))
    curso_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cursos.id"))
    pagamento_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pagamentos.id"))
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


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alunos.id"))
    gateway: Mapped[str] = mapped_column(String(40))
    gateway_transaction_id: Mapped[str] = mapped_column(
        String(120), unique=True, index=True  # garante idempotência do webhook
    )
    valor: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[StatusPagamento] = mapped_column(Enum(StatusPagamento))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    criado_em: Mapped[datetime] = _created_at()

    aluno: Mapped[Aluno | None] = relationship(back_populates="pagamentos")


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


# --------------------------------------------------------------------------- #
# Notificações de vigência / renovação (job agendado + login)
# --------------------------------------------------------------------------- #
class CanalNotificacao(str, enum.Enum):
    email = "email"
    whatsapp = "whatsapp"


class TipoNotificacao(str, enum.Enum):
    vigencia_proxima = "vigencia_proxima"     # ex: faltam 15/7/1 dias
    vigencia_expirada = "vigencia_expirada"
    promo_renovacao = "promo_renovacao"


class StatusNotificacao(str, enum.Enum):
    pendente = "pendente"
    enviada = "enviada"
    falhou = "falhou"


class Notificacao(Base):
    """Log de mensagens de vigência/renovação. Garante auditoria e idempotência:
    o job não reenvia o mesmo tipo para a mesma matrícula no mesmo marco."""
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
    marco: Mapped[str] = mapped_column(String(20))  # ex: "15d", "1d", "expirado"
    status: Mapped[StatusNotificacao] = mapped_column(
        Enum(StatusNotificacao), default=StatusNotificacao.pendente
    )
    provedor_msg_id: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    criado_em: Mapped[datetime] = _created_at()
    enviada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
