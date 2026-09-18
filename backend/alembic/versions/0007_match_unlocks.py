"""match_unlocks : les matchs ouverts par un compte gratuit, au prix d'un crédit hebdomadaire

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-18
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS match_unlocks (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            unlocked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_match_unlock_user_match UNIQUE (user_id, match_id)
        )""")
    # Le quota se compte par utilisateur sur la semaine en cours : c'est la
    # requête chaude, faite à chaque ouverture de match.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_match_unlocks_user_date ON match_unlocks (user_id, unlocked_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_match_unlocks_user_date")
    op.execute("DROP TABLE IF EXISTS match_unlocks")
