"""Réparation de données : la sélection d'Andorre était rattachée au club FC Andorra

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-23
"""
from alembic import op
from sqlalchemy.orm import Session

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.collectors.repairs import separer_andorre

    separer_andorre(Session(bind=op.get_bind()))


def downgrade() -> None:
    pass  # une réparation de données ne se défait pas
