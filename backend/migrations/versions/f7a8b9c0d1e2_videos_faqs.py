"""videos + faqs (cadastros do portal geridos pelo admin)

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("youtube_url", sa.String(length=500), nullable=True),
        sa.Column("duracao", sa.String(length=20), nullable=True),
        sa.Column("views", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "faqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pergunta", sa.String(length=300), nullable=False),
        sa.Column("resposta", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("faqs")
    op.drop_table("videos")
