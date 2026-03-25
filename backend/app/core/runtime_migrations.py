from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_runtime_columns(engine: Engine) -> None:
    """Apply lightweight runtime patches for existing DBs without Alembic."""
    with engine.begin() as conn:
        exists = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='matches' AND column_name='last_analyzed_at'"
        )).scalar()
        if not exists:
            conn.execute(text("ALTER TABLE matches ADD COLUMN last_analyzed_at TIMESTAMPTZ"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_matches_last_analyzed_at ON matches (last_analyzed_at)"))
