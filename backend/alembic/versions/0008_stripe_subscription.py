"""Identifiants Stripe sur l'abonnement, et résiliation en fin de période

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-18
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(64)")
    op.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(64)")
    op.execute(
        "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE"
    )
    # Unicité : deux abonnements ne peuvent pas désigner le même client ni le
    # même abonnement Stripe. Sans elle, un webhook rejoué pourrait créditer
    # deux comptes pour un seul paiement.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_subscriptions_stripe_customer ON subscriptions (stripe_customer_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_subscriptions_stripe_subscription ON subscriptions (stripe_subscription_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_subscriptions_stripe_subscription")
    op.execute("DROP INDEX IF EXISTS uq_subscriptions_stripe_customer")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS cancel_at_period_end")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS stripe_subscription_id")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS stripe_customer_id")
