"""cursos.status (em_desenvolvimento | ativo | inativo) — substitui cursos.ativo

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-06-27

Troca o booleano `ativo` por um enum de 3 estados. Backfill: ativo=true → 'ativo',
ativo=false → 'inativo'. Cursos novos nascem 'em_desenvolvimento' (server_default).
"""
from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status = sa.Enum(
        "em_desenvolvimento", "ativo", "inativo", name="statuscurso"
    )
    status.create(op.get_bind(), checkfirst=True)

    # Adiciona nullable, faz o backfill a partir do booleano e só então fixa
    # NOT NULL + default — evita violar a constraint nas linhas existentes.
    op.add_column(
        "cursos",
        sa.Column("status", status, nullable=True),
    )
    op.execute(
        "UPDATE cursos SET status = CASE WHEN ativo "
        "THEN 'ativo'::statuscurso ELSE 'inativo'::statuscurso END"
    )
    op.alter_column(
        "cursos",
        "status",
        nullable=False,
        server_default="em_desenvolvimento",
    )
    op.drop_column("cursos", "ativo")


def downgrade() -> None:
    op.add_column(
        "cursos",
        sa.Column(
            "ativo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute("UPDATE cursos SET ativo = (status = 'ativo'::statuscurso)")
    op.drop_column("cursos", "status")
    sa.Enum(name="statuscurso").drop(op.get_bind(), checkfirst=True)
