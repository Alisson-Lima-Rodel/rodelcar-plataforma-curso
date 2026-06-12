"""videos.likes (YouTube Data API)

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("likes", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("videos", "likes")
