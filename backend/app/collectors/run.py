"""CLI des collecteurs : python -m app.collectors.run {seed,fd_uk,fd_org,odds,fixtures,dedup,quarantine} [--seasons 2425 2526]
Écrit un heartbeat JSON dans backend/heartbeats/<nom>.json après chaque run réussi (lu par /health)."""
import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.collectors import fd_org, fd_uk, odds_api
from app.collectors.aliases import seed_aliases
from app.collectors.dedup import dedup_matches
from app.core.logging import setup_logging
from app.models.enums import MatchStatus
from app.models.match import Match
from app.services.settlement import settle_bets

HEARTBEATS = Path(__file__).resolve().parents[2] / "heartbeats"


def write_heartbeat(name: str, summary: dict) -> None:
    HEARTBEATS.mkdir(exist_ok=True)
    (HEARTBEATS / f"{name}.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **summary}), encoding="utf-8")


def quarantine_report(db: Session) -> dict[str, list[dict]]:
    """Noms d'équipes bruts (home_team/away_team) des matchs en QUARANTINE, groupés par compétition, triés par nom.
    Pour chaque nom : le nombre de matchs où il apparaît et son premier coup d'envoi. Fonction pure, pas d'I/O."""
    rows = db.scalars(select(Match).where(Match.status == MatchStatus.QUARANTINE)).all()
    by_comp: dict[str, dict[str, dict]] = {}
    for m in rows:
        names = by_comp.setdefault(m.competition, {})
        for raw_name in (m.home_team, m.away_team):
            entry = names.setdefault(raw_name, {"count": 0, "first_kickoff": m.kickoff_at})
            entry["count"] += 1
            if m.kickoff_at < entry["first_kickoff"]:
                entry["first_kickoff"] = m.kickoff_at
    return {
        comp: [{"name": name, **names[name]} for name in sorted(names)]
        for comp, names in sorted(by_comp.items())
    }


def print_quarantine_report(db: Session) -> None:
    report = quarantine_report(db)
    if not report:
        print("Aucun match en quarantaine.")
        return
    for comp, entries in report.items():
        print(f"--- {comp} ---")
        for e in entries:
            print(f"  {e['name']!r} : {e['count']} match(s), premier coup d'envoi {e['first_kickoff'].isoformat()}")
    print("\najouter ces noms dans KNOWN_TEAMS puis relancer seed et le collecteur")


def current_season(today: date | None = None) -> str:
    """Le code de saison football-data.co.uk (« 2627 » pour 2026/27) de la saison en cours.

    Une saison commence en août. Le crontab passait `--seasons 2526` en dur : depuis août 2026 il
    réimportait la saison précédente, complète et sans rien de neuf, et les résultats des championnats
    sans calendrier football-data.org (Serie B, 2. Bundesliga, Liga 2…) ne seraient jamais arrivés.
    """
    today = today or date.today()
    debut = today.year if today.month >= 8 else today.year - 1
    return f"{debut % 100:02d}{(debut + 1) % 100:02d}"


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    p = argparse.ArgumentParser()
    p.add_argument("collector", choices=["seed", "fd_uk", "fd_org", "odds", "fixtures", "dedup", "quarantine"])
    p.add_argument("--seasons", nargs="*", default=None, help="codes fd_uk (ex. 2526 2627) ; défaut : la saison en cours")
    args = p.parse_args(argv)
    db = next(get_db())
    try:
        if args.collector == "quarantine":
            print_quarantine_report(db)
            return 0
        if args.collector == "seed":
            n = seed_aliases(db); summary = {"aliases_created": n}
        elif args.collector == "fd_uk":
            reports = fd_uk.run(db, args.seasons or [current_season()]); summary = {k: vars(v) for k, v in reports.items()}
        elif args.collector == "fd_org":
            summary = vars(fd_org.run(db))
            summary["bets_settled"] = settle_bets(db)
        elif args.collector == "fixtures":
            summary = vars(fd_uk.run_fixtures(db))
        elif args.collector == "dedup":
            report = dedup_matches(db)
            summary = vars(report)
            print(report)
        else:
            summary = vars(odds_api.run(db))
        write_heartbeat(args.collector, summary)
        logging.getLogger("rushplay.collectors").info("%s terminé : %s", args.collector, summary)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
