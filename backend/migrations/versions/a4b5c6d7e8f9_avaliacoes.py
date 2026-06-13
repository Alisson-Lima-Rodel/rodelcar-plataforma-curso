"""avaliacoes (review de curso por aluno matriculado)

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "avaliacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "aluno_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alunos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "curso_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cursos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nota", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Aprovado"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("aluno_id", "curso_id", name="uq_avaliacao_aluno_curso"),
    )
    op.create_index("ix_avaliacoes_aluno_id", "avaliacoes", ["aluno_id"])
    op.create_index("ix_avaliacoes_curso_id", "avaliacoes", ["curso_id"])


def downgrade() -> None:
    op.drop_index("ix_avaliacoes_curso_id", table_name="avaliacoes")
    op.drop_index("ix_avaliacoes_aluno_id", table_name="avaliacoes")
    op.drop_table("avaliacoes")
