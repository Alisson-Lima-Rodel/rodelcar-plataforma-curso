"""google_review_cache (cache da nota/avaliações do Google)

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-06-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_review_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rating", sa.Numeric(2, 1), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reviews", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("google_review_cache")
