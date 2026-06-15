"""quiz por módulo (quizzes, questoes, alternativas, tentativas_quiz)

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a0b1c2d3e4f5"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "modulo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("modulos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("nota_corte", sa.Numeric(5, 2), nullable=False, server_default="70"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("modulo_id", name="uq_quiz_modulo"),
    )
    op.create_index("ix_quizzes_modulo_id", "quizzes", ["modulo_id"])

    op.create_table(
        "questoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "quiz_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quizzes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enunciado", sa.Text(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_questoes_quiz_id", "questoes", ["quiz_id"])

    op.create_table(
        "alternativas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "questao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("texto", sa.String(length=500), nullable=False),
        sa.Column("correta", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_alternativas_questao_id", "alternativas", ["questao_id"])

    op.create_table(
        "tentativas_quiz",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "matricula_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("matriculas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "quiz_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quizzes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nota", sa.Numeric(5, 2), nullable=False),
        sa.Column("aprovado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("respostas", postgresql.JSONB(), server_default="{}"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tentativas_quiz_matricula_id", "tentativas_quiz", ["matricula_id"])
    op.create_index("ix_tentativas_quiz_quiz_id", "tentativas_quiz", ["quiz_id"])


def downgrade() -> None:
    op.drop_table("tentativas_quiz")
    op.drop_table("alternativas")
    op.drop_table("questoes")
    op.drop_table("quizzes")
