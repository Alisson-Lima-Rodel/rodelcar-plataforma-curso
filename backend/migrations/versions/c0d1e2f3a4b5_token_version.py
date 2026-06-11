"""token_version em alunos e admins (revogação de sessão / access token)

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default "0" preenche as linhas existentes; tokens antigos (sem claim
    # "tv") são tratados como tv=0 no app, então continuam válidos após a migração.
    op.add_column(
        "alunos",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "admins",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("admins", "token_version")
    op.drop_column("alunos", "token_version")
