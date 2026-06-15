"""indique-e-ganhe: alunos.codigo_indicacao + tabela indicacoes

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-06-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alunos", sa.Column("codigo_indicacao", sa.String(length=20), nullable=True)
    )
    op.create_index(
        "ix_alunos_codigo_indicacao", "alunos", ["codigo_indicacao"], unique=True
    )
    op.create_table(
        "indicacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "indicador_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alunos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "indicado_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alunos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),
        sa.Column(
            "cupom_indicador_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cupons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cupom_indicado_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cupons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("recompensado_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("indicado_id", name="uq_indicacao_indicado"),
    )
    op.create_index("ix_indicacoes_indicador_id", "indicacoes", ["indicador_id"])
    op.create_index("ix_indicacoes_indicado_id", "indicacoes", ["indicado_id"])


def downgrade() -> None:
    op.drop_index("ix_indicacoes_indicado_id", table_name="indicacoes")
    op.drop_index("ix_indicacoes_indicador_id", table_name="indicacoes")
    op.drop_table("indicacoes")
    op.drop_index("ix_alunos_codigo_indicacao", table_name="alunos")
    op.drop_column("alunos", "codigo_indicacao")
