"""ajustes admin: cursos.ativo, alunos.bloqueado, password_resets

Revision ID: b0c1d2e3f4a5
Revises: c2d3e4f5a6b7
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b0c1d2e3f4a5"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Curso ativo/inativo (default ativo p/ não esconder o catálogo existente).
    op.add_column(
        "cursos",
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
    )
    # Bloqueio manual de acesso do aluno.
    op.add_column(
        "alunos",
        sa.Column("bloqueado", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Tokens de redefinição de senha (single-use, gerados pelo admin).
    op.create_table(
        "password_resets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "aluno_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alunos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_password_resets_aluno_id", "password_resets", ["aluno_id"])
    op.create_index(
        "ix_password_resets_token_hash", "password_resets", ["token_hash"], unique=True
    )

    # eventos.aluno_id agora é usado (login/aula assistida). ON DELETE SET NULL:
    # excluir um aluno não viola a FK nem apaga o histórico de eventos.
    op.drop_constraint("eventos_aluno_id_fkey", "eventos", type_="foreignkey")
    op.create_foreign_key(
        "eventos_aluno_id_fkey",
        "eventos",
        "alunos",
        ["aluno_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("eventos_aluno_id_fkey", "eventos", type_="foreignkey")
    op.create_foreign_key(
        "eventos_aluno_id_fkey", "eventos", "alunos", ["aluno_id"], ["id"]
    )
    op.drop_index("ix_password_resets_token_hash", table_name="password_resets")
    op.drop_index("ix_password_resets_aluno_id", table_name="password_resets")
    op.drop_table("password_resets")
    op.drop_column("alunos", "bloqueado")
    op.drop_column("cursos", "ativo")
