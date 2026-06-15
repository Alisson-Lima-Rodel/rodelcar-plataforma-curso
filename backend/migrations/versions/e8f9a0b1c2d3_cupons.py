"""cupons (Stripe Coupon + Promotion Code; recompensa de referral)

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-06-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cupons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("stripe_coupon_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_promotion_code_id", sa.String(length=255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_resgates", sa.Integer(), nullable=True),
        sa.Column("validade", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "aluno_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alunos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("codigo", name="uq_cupom_codigo"),
    )
    op.create_index("ix_cupons_codigo", "cupons", ["codigo"])
    op.create_index("ix_cupons_aluno_id", "cupons", ["aluno_id"])


def downgrade() -> None:
    op.drop_index("ix_cupons_aluno_id", table_name="cupons")
    op.drop_index("ix_cupons_codigo", table_name="cupons")
    op.drop_table("cupons")
