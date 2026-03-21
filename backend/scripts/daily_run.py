from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.database import SessionLocal
from app.core.runtime_migrations import ensure_runtime_columns
from app.core.database import engine
from app.models.analysis import Analysis
from app.models.enums import MatchStatus
from app.models.match import Match
from app.services.analysis_runner import run_bulk_analyses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RushPlay daily analysis batch")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of matches to process")
    parser.add_argument("--league", type=str, default=None, help="Optional league filter")
    parser.add_argument("--only-missing", action="store_true", help="Process only matches without analysis")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    ensure_runtime_columns(engine)

    with SessionLocal() as db:
        query = select(Match).where(Match.status == MatchStatus.SCHEDULED).order_by(Match.kickoff_at.asc())

        if args.league:
            query = query.where(Match.league.ilike(f"%{args.league}%"))

        if args.only_missing:
            query = query.outerjoin(Analysis).where(Analysis.id.is_(None))

        if args.limit and args.limit > 0:
            query = query.limit(args.limit)

        matches = db.scalars(query).all()

        if not matches:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "No scheduled matches found",
                "summary": {"processed": 0, "created": 0, "updated": 0, "failed": 0, "errors": []},
            }
            print(json.dumps(payload, ensure_ascii=True))
            return 0

        summary = run_bulk_analyses(db, matches)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Daily run completed",
        "summary": summary,
    }
    print(json.dumps(payload, ensure_ascii=True))

    return 0 if summary.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
