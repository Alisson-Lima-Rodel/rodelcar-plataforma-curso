"""aulas.panda_external_id (id do embed do Panda — ?v=, difere do id da API)

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-28

O player do Panda embeda por `video_external_id` (vai no ?v=), que DIFERE do
`panda_video_id` (id da REST API, usado em sync/retenção). Sem guardar os dois, o
embed usa o id errado e o player mostra falha. Idempotente (ADD/DROP IF [NOT] EXISTS)
porque a coluna pode já ter sido criada via SQL direto no Supabase.
"""
from alembic import op

revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE aulas ADD COLUMN IF NOT EXISTS panda_external_id VARCHAR(120)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE aulas DROP COLUMN IF EXISTS panda_external_id")
