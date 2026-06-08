"""curso marketing fields (vitrine / página de venda)

Revision ID: b2c3d4e5f6a7
Revises: c3d4e5f6a7b8
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "b2c3d4e5f6a7"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cursos", sa.Column("tagline", sa.String(length=300), nullable=True))
    op.add_column("cursos", sa.Column("preco_antigo", sa.Numeric(10, 2), nullable=True))
    op.add_column("cursos", sa.Column("horas", sa.String(length=20), nullable=True))
    op.add_column("cursos", sa.Column("aulas_total", sa.Integer(), server_default="0", nullable=False))
    op.add_column("cursos", sa.Column("rating", sa.Numeric(2, 1), nullable=True))
    op.add_column("cursos", sa.Column("alunos", sa.Integer(), server_default="0", nullable=False))
    op.add_column("cursos", sa.Column("nivel", sa.String(length=40), nullable=True))
    op.add_column("cursos", sa.Column("icon", sa.String(length=40), nullable=True))
    op.add_column("cursos", sa.Column("badge_label", sa.String(length=40), nullable=True))
    op.add_column("cursos", sa.Column("aprende", JSONB(), server_default="[]", nullable=False))


def downgrade() -> None:
    for col in (
        "aprende", "badge_label", "icon", "nivel", "alunos",
        "rating", "aulas_total", "horas", "preco_antigo", "tagline",
    ):
        op.drop_column("cursos", col)
