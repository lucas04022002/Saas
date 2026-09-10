"""lecture du marché : teams, team_aliases, odds_snapshots, bets ; matches étendu ; tables ML supprimées

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-10
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS warning_points CASCADE")
    op.execute("DROP TABLE IF EXISTS team_stats CASCADE")
    op.execute("DROP TABLE IF EXISTS analyses CASCADE")
    op.execute("DROP TYPE IF EXISTS risklevel")
    op.execute("DROP TYPE IF EXISTS teamtype")
    op.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL UNIQUE,
            country VARCHAR(120) NOT NULL
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS team_aliases (
            id UUID PRIMARY KEY,
            source VARCHAR(16) NOT NULL,
            alias VARCHAR(120) NOT NULL,
            team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            CONSTRAINT uq_alias_source UNIQUE (source, alias)
        )""")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS fd_uk_key VARCHAR(160) UNIQUE")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition VARCHAR(8) NOT NULL DEFAULT 'E0'")
    op.execute("ALTER TABLE matches ALTER COLUMN competition DROP DEFAULT")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_competition ON matches (competition)")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_team_id UUID REFERENCES teams(id)")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_team_id UUID REFERENCES teams(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_home_team_id ON matches (home_team_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_away_team_id ON matches (away_team_id)")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_shots INTEGER")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_shots INTEGER")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS home_team_ext_id")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS away_team_ext_id")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS last_analyzed_at")
    op.execute("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'POSTPONED'")
    op.execute("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'QUARANTINE'")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_match_natural') THEN
                ALTER TABLE matches ADD CONSTRAINT uq_match_natural UNIQUE (competition, kickoff_at, home_team_id, away_team_id);
            END IF;
        END $$""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id UUID PRIMARY KEY,
            match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            bookmaker VARCHAR(40) NOT NULL,
            taken_at TIMESTAMPTZ NOT NULL,
            home DOUBLE PRECISION NOT NULL,
            draw DOUBLE PRECISION NOT NULL,
            away DOUBLE PRECISION NOT NULL,
            CONSTRAINT uq_snapshot UNIQUE (match_id, bookmaker, taken_at)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_odds_snapshots_match_id ON odds_snapshots (match_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_odds_snapshots_taken_at ON odds_snapshots (taken_at)")
    op.execute("DO $$ BEGIN CREATE TYPE outcome AS ENUM ('home','draw','away'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE betstatus AS ENUM ('PENDING','WON','LOST','VOID'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            match_id UUID NOT NULL REFERENCES matches(id),
            outcome outcome NOT NULL,
            bookmaker VARCHAR(40) NOT NULL,
            odds DOUBLE PRECISION NOT NULL,
            stake DOUBLE PRECISION NOT NULL,
            status betstatus NOT NULL DEFAULT 'PENDING',
            payout DOUBLE PRECISION,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            settled_at TIMESTAMPTZ
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bets_user_id ON bets (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bets_match_id ON bets (match_id)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS birth_date")
    op.execute("DROP TABLE IF EXISTS bets")
    op.execute("DROP TABLE IF EXISTS odds_snapshots")
    op.execute("ALTER TABLE matches DROP CONSTRAINT IF EXISTS uq_match_natural")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS home_team_id, DROP COLUMN IF EXISTS away_team_id, DROP COLUMN IF EXISTS competition, DROP COLUMN IF EXISTS fd_uk_key, DROP COLUMN IF EXISTS home_shots, DROP COLUMN IF EXISTS away_shots")
    op.execute("DROP TABLE IF EXISTS team_aliases")
    op.execute("DROP TABLE IF EXISTS teams")
    op.execute("DROP TYPE IF EXISTS betstatus")
    op.execute("DROP TYPE IF EXISTS outcome")
