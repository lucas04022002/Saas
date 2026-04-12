"""add home_score and away_score to matches

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-12
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_score INTEGER")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_score INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS home_score")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS away_score")
