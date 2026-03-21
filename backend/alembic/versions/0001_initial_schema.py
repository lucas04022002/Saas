"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums ---
    userrole = postgresql.ENUM("USER", "ADMIN", name="userrole", create_type=False)
    userrole.create(op.get_bind(), checkfirst=True)

    subscriptionplan = postgresql.ENUM("STARTER", "PRO", "ELITE", name="subscriptionplan", create_type=False)
    subscriptionplan.create(op.get_bind(), checkfirst=True)

    subscriptionstatus = postgresql.ENUM("ACTIVE", "CANCELED", "PAST_DUE", name="subscriptionstatus", create_type=False)
    subscriptionstatus.create(op.get_bind(), checkfirst=True)

    matchstatus = postgresql.ENUM("SCHEDULED", "LIVE", "FINISHED", name="matchstatus", create_type=False)
    matchstatus.create(op.get_bind(), checkfirst=True)

    risklevel = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="risklevel", create_type=False)
    risklevel.create(op.get_bind(), checkfirst=True)

    teamtype = postgresql.ENUM("home", "away", name="teamtype", create_type=False)
    teamtype.create(op.get_bind(), checkfirst=True)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("USER", "ADMIN", name="userrole"), nullable=False),
        sa.Column("subscription_plan", sa.Enum("STARTER", "PRO", "ELITE", name="subscriptionplan"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- matches ---
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(120), nullable=True, unique=True),
        sa.Column("home_team", sa.String(120), nullable=False),
        sa.Column("away_team", sa.String(120), nullable=False),
        sa.Column("league", sa.String(120), nullable=False),
        sa.Column("country", sa.String(120), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("SCHEDULED", "LIVE", "FINISHED", name="matchstatus"), nullable=False),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_matches_league", "matches", ["league"])
    op.create_index("ix_matches_kickoff_at", "matches", ["kickoff_at"])
    op.create_index("ix_matches_last_analyzed_at", "matches", ["last_analyzed_at"])

    # --- analyses ---
    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matches.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("recommended_bet", sa.String(120), nullable=False),
        sa.Column("bookmaker_odds", sa.Float, nullable=False),
        sa.Column("value_percent", sa.Float, nullable=False),
        sa.Column("risk_level", sa.Enum("LOW", "MEDIUM", "HIGH", name="risklevel"), nullable=False),
        sa.Column("ai_explanation", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analyses_confidence_score", "analyses", ["confidence_score"])
    op.create_index("ix_analyses_value_percent", "analyses", ["value_percent"])

    # --- warning_points ---
    op.create_table(
        "warning_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- team_stats ---
    op.create_table(
        "team_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_type", sa.Enum("home", "away", name="teamtype"), nullable=False),
        sa.Column("recent_form", sa.String(20), nullable=False),
        sa.Column("goals_scored", sa.Integer, nullable=False),
        sa.Column("goals_conceded", sa.Integer, nullable=False),
        sa.Column("xg", sa.Float, nullable=False),
        sa.Column("xga", sa.Float, nullable=False),
        sa.Column("possession_avg", sa.Float, nullable=False),
        sa.Column("shots_on_target_avg", sa.Float, nullable=False),
        sa.Column("clean_sheets", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("plan", sa.Enum("STARTER", "PRO", "ELITE", name="subscriptionplan"), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "CANCELED", "PAST_DUE", name="subscriptionstatus"), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- favorites ---
    op.create_table(
        "favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "match_id", name="uq_favorite_user_match"),
    )


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("subscriptions")
    op.drop_table("team_stats")
    op.drop_table("warning_points")
    op.drop_table("analyses")
    op.drop_table("matches")
    op.drop_table("users")

    for enum_name in ("teamtype", "risklevel", "matchstatus", "subscriptionstatus", "subscriptionplan", "userrole"):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
