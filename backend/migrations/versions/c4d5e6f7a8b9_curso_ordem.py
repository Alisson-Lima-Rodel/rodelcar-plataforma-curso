"""curso ordem (ordenação curada da vitrine)

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cursos", sa.Column("ordem", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("cursos", "ordem")
