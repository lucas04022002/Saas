"""Mesure des réseaux : source de l'inscription + compteur des arrivées par `?ref=`

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-01
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_source VARCHAR(32)")
    op.execute(
        "CREATE TABLE IF NOT EXISTS source_visits ("
        " day DATE NOT NULL,"
        " source VARCHAR(32) NOT NULL,"
        " visits INTEGER NOT NULL DEFAULT 0,"
        " PRIMARY KEY (day, source))"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source_visits")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS signup_source")
