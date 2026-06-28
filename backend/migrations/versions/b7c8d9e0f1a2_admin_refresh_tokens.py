"""admin_refresh_tokens (refresh STATEFUL do painel admin — espelha refresh_tokens)

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-06-28

O admin passa a usar refresh stateful (jti em tabela, rotação e detecção de reuso),
a MESMA regra segura do aluno. Tabela espelha `refresh_tokens`, mas com
`admin_id` → `admins`. Idempotente no create (IF NOT EXISTS) para tolerar
aplicação manual prévia.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_refresh_tokens (
            id           uuid PRIMARY KEY,
            admin_id     uuid NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
            jti          uuid NOT NULL,
            expira_em    timestamptz NOT NULL,
            revogado     boolean NOT NULL DEFAULT false,
            revogado_em  timestamptz,
            criado_em    timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_admin_refresh_tokens_jti "
        "ON admin_refresh_tokens (jti)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_admin_refresh_tokens_admin_id "
        "ON admin_refresh_tokens (admin_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_refresh_tokens")
