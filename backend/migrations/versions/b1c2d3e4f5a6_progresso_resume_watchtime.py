"""progresso: posicao_segundos + segundos_assistidos (resume + gate anti-fraude)

posicao_segundos = último segundo assistido (seek de retomada cross-device).
segundos_assistidos = tempo real assistido, acumulado pelo servidor; gate do
certificado exige >= CERT_MIN_WATCH_RATIO * duracao_segundos por aula.

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "progresso",
        sa.Column("posicao_segundos", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "progresso",
        sa.Column(
            "segundos_assistidos", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("progresso", "segundos_assistidos")
    op.drop_column("progresso", "posicao_segundos")
