"""turmas_midia (fotos das turmas presenciais — mosaico bento da home)

Revision ID: d3e4f5a6b7c8
Revises: b0c1d2e3f4a5
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d3e4f5a6b7c8"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "turmas_midia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("alt", sa.String(length=300), nullable=True),
        sa.Column("destaque", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("turmas_midia")
