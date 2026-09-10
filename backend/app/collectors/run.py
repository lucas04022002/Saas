"""CLI des collecteurs : python -m app.collectors.run {seed,fd_uk,fd_org,odds} [--seasons 2425 2526]
Écrit un heartbeat JSON dans backend/heartbeats/<nom>.json après chaque run réussi (lu par /health)."""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.api.deps import get_db
from app.collectors import fd_org, fd_uk, odds_api
from app.collectors.aliases import seed_aliases
from app.core.logging import setup_logging
from app.services.settlement import settle_bets

HEARTBEATS = Path(__file__).resolve().parents[2] / "heartbeats"


def write_heartbeat(name: str, summary: dict) -> None:
    HEARTBEATS.mkdir(exist_ok=True)
    (HEARTBEATS / f"{name}.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **summary}), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    p = argparse.ArgumentParser()
    p.add_argument("collector", choices=["seed", "fd_uk", "fd_org", "odds"])
    p.add_argument("--seasons", nargs="*", default=["2526"])
    args = p.parse_args(argv)
    db = next(get_db())
    try:
        if args.collector == "seed":
            n = seed_aliases(db); summary = {"aliases_created": n}
        elif args.collector == "fd_uk":
            reports = fd_uk.run(db, args.seasons); summary = {k: vars(v) for k, v in reports.items()}
        elif args.collector == "fd_org":
            summary = vars(fd_org.run(db))
            summary["bets_settled"] = settle_bets(db)
        else:
            summary = vars(odds_api.run(db))
        write_heartbeat(args.collector, summary)
        logging.getLogger("rushplay.collectors").info("%s terminé : %s", args.collector, summary)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
