"""Battements de cœur des collecteurs en base (le volume `heartbeats/` était illisible sans root)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-23
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS collector_heartbeats ("
        " name VARCHAR(32) PRIMARY KEY,"
        " at TIMESTAMP WITH TIME ZONE NOT NULL,"
        " summary TEXT NOT NULL DEFAULT '{}')"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collector_heartbeats")
