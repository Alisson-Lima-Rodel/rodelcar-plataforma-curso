"""videos.canal + videos.estrelas (enriquecimento do card)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("canal", sa.String(length=120), nullable=True))
    op.add_column(
        "videos",
        sa.Column("estrelas", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("videos", "estrelas")
    op.drop_column("videos", "canal")
