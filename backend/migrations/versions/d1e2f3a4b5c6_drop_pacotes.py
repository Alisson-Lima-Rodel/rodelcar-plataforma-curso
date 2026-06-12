"""remove a tabela pacotes (substituída pelos planos de assinatura)

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pacotes eram combos de marketing sem integração de venda; os planos de
    # assinatura (planos_assinatura, ligados à Stripe) cumprem o papel.
    op.drop_table("pacotes")


def downgrade() -> None:
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
