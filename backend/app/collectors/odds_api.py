"""The Odds API : relevés 1N2 des bookmakers français + Pinnacle, archivés tels quels (jamais écrasés)."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS, FRENCH_BOOKMAKERS, REFERENCE_BOOKMAKER, by_odds_api_key
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot

log = logging.getLogger("rushplay.collectors.odds_api")
BASE = "https://api.the-odds-api.com/v4/sports"
KEPT_BOOKMAKERS = set(FRENCH_BOOKMAKERS) | {REFERENCE_BOOKMAKER}


@dataclass
class OddsEvent:
    competition_code: str
    commence: datetime
    home: str
    away: str
    books: dict[str, tuple[float, float, float]] = field(default_factory=dict)


@dataclass
class StoreReport:
    snapshots: int = 0
    matched: int = 0
    unmatched: int = 0
    quarantined: int = 0


def parse_events(sport_key: str, payload: list) -> list[OddsEvent]:
    comp = by_odds_api_key(sport_key)
    if comp is None:
        return []
    events = []
    for e in payload:
        ev = OddsEvent(competition_code=comp.code, commence=datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")),
                       home=e["home_team"], away=e["away_team"])
        for b in e.get("bookmakers", []):
            if b["key"] not in KEPT_BOOKMAKERS:
                continue
            h2h = next((m for m in b.get("markets", []) if m["key"] == "h2h"), None)
            if h2h is None:
                continue
            prices = {o["name"]: float(o["price"]) for o in h2h["outcomes"]}
            if ev.home in prices and ev.away in prices and "Draw" in prices:
                ev.books[b["key"]] = (prices[ev.home], prices["Draw"], prices[ev.away])
        if ev.books:
            events.append(ev)
    return events


def _find_or_create_match(db: Session, ev: OddsEvent, home, away) -> Match:
    comp = COMPETITIONS[ev.competition_code]
    day = ev.commence.date()
    window = (datetime.combine(day - timedelta(days=1), time.min, tzinfo=timezone.utc),
              datetime.combine(day + timedelta(days=1), time.max, tzinfo=timezone.utc))
    match = db.scalar(select(Match).where(Match.competition == comp.code, Match.home_team_id == home.id, Match.away_team_id == away.id,
                                          Match.kickoff_at >= window[0], Match.kickoff_at <= window[1]))
    if match is None:
        match = Match(competition=comp.code, league=comp.name, country=comp.country, home_team_id=home.id, away_team_id=away.id,
                      home_team=home.name, away_team=away.name, kickoff_at=ev.commence, status=MatchStatus.SCHEDULED)
        db.add(match); db.flush()
    return match


def store_events(db: Session, events: list[OddsEvent], taken_at: datetime) -> StoreReport:
    report = StoreReport()
    for ev in events:
        try:
            home, away = resolve_team(db, "odds_api", ev.home), resolve_team(db, "odds_api", ev.away)
        except TeamAliasError as e:
            log.warning("quarantaine odds_api %s v %s : %s", ev.home, ev.away, e)
            report.quarantined += 1
            continue
        match = _find_or_create_match(db, ev, home, away)
        report.matched += 1
        for book, (h, d, a) in ev.books.items():
            exists = db.scalar(select(OddsSnapshot.id).where(OddsSnapshot.match_id == match.id, OddsSnapshot.bookmaker == book, OddsSnapshot.taken_at == taken_at))
            if exists:
                continue
            db.add(OddsSnapshot(match_id=match.id, bookmaker=book, taken_at=taken_at, home=h, draw=d, away=a))
            report.snapshots += 1
        db.commit()
    return report


def fetch_sport(sport_key: str) -> list:
    """1 crédit par région → 2 crédits par compétition et par relevé."""
    resp = requests.get(f"{BASE}/{sport_key}/odds",
                        params={"apiKey": settings.the_odds_api_key, "regions": "fr,eu", "markets": "h2h", "oddsFormat": "decimal"}, timeout=30)
    resp.raise_for_status()
    remaining = resp.headers.get("x-requests-remaining")
    log.info("odds_api %s : %s événements, crédits restants %s", sport_key, len(resp.json()), remaining)
    return resp.json()


def run(db: Session) -> StoreReport:
    """Un relevé complet = 6 compétitions × 2 régions = 12 crédits. L'horodatage est arrondi à l'heure."""
    taken_at = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    total = StoreReport()
    for comp in COMPETITIONS.values():
        try:
            payload = fetch_sport(comp.odds_api_key)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                log.error("odds_api : quota épuisé ou clé invalide, arrêt propre du relevé")
                break
            raise
        r = store_events(db, parse_events(comp.odds_api_key, payload), taken_at)
        for k in ("snapshots", "matched", "unmatched", "quarantined"):
            setattr(total, k, getattr(total, k) + getattr(r, k))
    log.info("odds_api relevé %s : %s", taken_at.isoformat(), total)
    return total
