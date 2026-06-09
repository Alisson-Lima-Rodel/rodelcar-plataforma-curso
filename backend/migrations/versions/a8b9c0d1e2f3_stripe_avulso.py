"""stripe avulso: stripe_customer_id, stripe_price_id, webhook_eventos

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alunos", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_alunos_stripe_customer_id", "alunos", ["stripe_customer_id"], unique=True
    )

    op.add_column("cursos", sa.Column("stripe_price_id", sa.String(length=255), nullable=True))

    op.create_table(
        "webhook_eventos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("gateway", sa.String(length=40), nullable=False),
        sa.Column("tipo", sa.String(length=120), nullable=False),
        sa.Column("processado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_webhook_eventos_event_id", "webhook_eventos", ["event_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_eventos_event_id", table_name="webhook_eventos")
    op.drop_table("webhook_eventos")
    op.drop_column("cursos", "stripe_price_id")
    op.drop_index("ix_alunos_stripe_customer_id", table_name="alunos")
    op.drop_column("alunos", "stripe_customer_id")
