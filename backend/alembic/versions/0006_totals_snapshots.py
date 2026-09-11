"""totals_snapshots : cotes over/under du marché (Pinnacle) pour le total de buts attendu

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-11
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS totals_snapshots (
            id UUID PRIMARY KEY,
            match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            bookmaker VARCHAR(32) NOT NULL,
            taken_at TIMESTAMPTZ NOT NULL,
            line DOUBLE PRECISION NOT NULL,
            over DOUBLE PRECISION NOT NULL,
            under DOUBLE PRECISION NOT NULL,
            CONSTRAINT uq_totals_snapshot UNIQUE (match_id, bookmaker, taken_at, line)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_totals_snapshots_match_id ON totals_snapshots (match_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS totals_snapshots")
