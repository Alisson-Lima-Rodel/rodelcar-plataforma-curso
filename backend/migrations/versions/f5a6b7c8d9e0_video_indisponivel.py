"""videos.indisponivel (vídeo fora do ar no YouTube — escondido da capa)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-27

Flag setada pelo job diário quando o vídeo some do YouTube (apagado/privado). O
endpoint público filtra por ela; volta a aparecer sozinho se o vídeo reaparecer.
"""
from alembic import op
import sqlalchemy as sa

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column(
            "indisponivel",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("videos", "indisponivel")
