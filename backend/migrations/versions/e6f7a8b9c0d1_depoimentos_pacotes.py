"""depoimentos + pacotes (cadastros do admin)

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "depoimentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("papel", sa.String(length=160), nullable=True),
        sa.Column("estrelas", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Pendente"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "pacotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("preco_antigo", sa.Numeric(10, 2), nullable=True),
        sa.Column("parcelas", sa.String(length=80), nullable=True),
        sa.Column("cursos", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("inclui", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("pacotes")
    op.drop_table("depoimentos")
