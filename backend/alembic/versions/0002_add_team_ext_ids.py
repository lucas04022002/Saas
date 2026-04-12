"""add home/away team ext ids to matches

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-12
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_team_ext_id VARCHAR(50)")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_team_ext_id VARCHAR(50)")


def downgrade() -> None:
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS home_team_ext_id")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS away_team_ext_id")
