"""stripe assinaturas: matriculas.stripe_subscription_id + planos_assinatura

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matriculas", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True)
    )
    op.create_index(
        "ix_matriculas_stripe_subscription_id",
        "matriculas",
        ["stripe_subscription_id"],
    )

    op.create_table(
        "planos_assinatura",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("intervalo", sa.String(length=20), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=False),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_planos_assinatura_stripe_price_id",
        "planos_assinatura",
        ["stripe_price_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_planos_assinatura_stripe_price_id", table_name="planos_assinatura")
    op.drop_table("planos_assinatura")
    op.drop_index("ix_matriculas_stripe_subscription_id", table_name="matriculas")
    op.drop_column("matriculas", "stripe_subscription_id")
