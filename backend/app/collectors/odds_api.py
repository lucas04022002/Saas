"""The Odds API : relevés 1N2 des bookmakers français + Pinnacle (archivés tels quels, jamais écrasés), et
relevé du total de buts (over/under) Pinnacle seul — sert à app.engine.score.expected_total, cf.
docs/mesures/2026-09-11-score-le-plus-probable.md (complément du 11/09/2026)."""
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS, FRENCH_BOOKMAKERS, REFERENCE_BOOKMAKER, by_odds_api_key
from app.collectors.dedup import find_existing
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.totals_snapshot import TotalsSnapshot

log = logging.getLogger("rushplay.collectors.odds_api")
BASE = "https://api.the-odds-api.com/v4/sports"
KEPT_BOOKMAKERS = set(FRENCH_BOOKMAKERS) | {REFERENCE_BOOKMAKER}
EventKey = tuple[str, str, datetime]   # (home, away, commence) tel que rendu par l'API — sert à rapprocher les
                                        # événements du relevé h2h et du relevé totals sans les résoudre deux fois


@dataclass
class OddsEvent:
    competition_code: str
    commence: datetime
    home: str
    away: str
    books: dict[str, tuple[float, float, float]] = field(default_factory=dict)


@dataclass
class TotalsEvent:
    competition_code: str
    commence: datetime
    home: str
    away: str
    lines: dict[float, tuple[float, float]] = field(default_factory=dict)   # ligne -> (over, under), Pinnacle seul


@dataclass
class StoreReport:
    snapshots: int = 0
    matched: int = 0
    quarantined: int = 0
    totals: int = 0
    event_matches: dict[EventKey, uuid.UUID] = field(default_factory=dict)   # rempli par store_events, lu par store_totals


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


def parse_totals(sport_key: str, payload: list) -> list[TotalsEvent]:
    """Marché `totals` (over/under), Pinnacle seul (région `eu`, 1 crédit) : une ligne par (event, point)."""
    comp = by_odds_api_key(sport_key)
    if comp is None:
        return []
    events = []
    for e in payload:
        ev = TotalsEvent(competition_code=comp.code, commence=datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")),
                         home=e["home_team"], away=e["away_team"])
        for b in e.get("bookmakers", []):
            if b["key"] != REFERENCE_BOOKMAKER:
                continue
            totals_market = next((m for m in b.get("markets", []) if m["key"] == "totals"), None)
            if totals_market is None:
                continue
            by_line: dict[float, dict[str, float]] = defaultdict(dict)
            for o in totals_market.get("outcomes", []):
                if "point" not in o:
                    continue
                by_line[float(o["point"])][o["name"]] = float(o["price"])
            for line, prices in by_line.items():
                if "Over" in prices and "Under" in prices:
                    ev.lines[line] = (prices["Over"], prices["Under"])
        if ev.lines:
            events.append(ev)
    return events


def _find_or_create_match(db: Session, ev: OddsEvent, home, away) -> Match:
    comp = COMPETITIONS[ev.competition_code]
    # un match posé par fd_uk ou fd_org pour ces équipes/cette compétition, à coup d'envoi proche, peut déjà
    # exister sans que l'odds_api ait de moyen de le rapprocher par identifiant (il n'en a pas)
    match = find_existing(db, comp.code, home.id, away.id, ev.commence)
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
        snapshots = 0
        try:
            match = _find_or_create_match(db, ev, home, away)
            report.event_matches[(ev.home, ev.away, ev.commence)] = match.id
            for book, (h, d, a) in ev.books.items():
                exists = db.scalar(select(OddsSnapshot.id).where(OddsSnapshot.match_id == match.id, OddsSnapshot.bookmaker == book, OddsSnapshot.taken_at == taken_at))
                if exists:
                    continue
                db.add(OddsSnapshot(match_id=match.id, bookmaker=book, taken_at=taken_at, home=h, draw=d, away=a))
                snapshots += 1
            db.commit()
            report.matched += 1
            report.snapshots += snapshots
        except IntegrityError:
            db.rollback()
            log.warning("conflit d'unicité odds_api ignoré (%s v %s)", ev.home, ev.away)
    return report


def store_totals(db: Session, events: list[TotalsEvent], taken_at: datetime, event_matches: dict[EventKey, uuid.UUID] | None = None) -> StoreReport:
    """Rapproche chaque événement totals d'un match, en priorité via `event_matches` (déjà résolu par le relevé
    h2h de ce même passage) pour éviter de résoudre les équipes deux fois ; sinon résout comme `store_events`."""
    event_matches = event_matches or {}
    report = StoreReport()
    for ev in events:
        key = (ev.home, ev.away, ev.commence)
        match_id = event_matches.get(key)
        if match_id is None:
            try:
                home, away = resolve_team(db, "odds_api", ev.home), resolve_team(db, "odds_api", ev.away)
            except TeamAliasError as e:
                log.warning("quarantaine odds_api totals %s v %s : %s", ev.home, ev.away, e)
                report.quarantined += 1
                continue
            try:
                match = _find_or_create_match(db, ev, home, away)
            except IntegrityError:
                db.rollback()
                log.warning("conflit d'unicité odds_api totals ignoré (%s v %s)", ev.home, ev.away)
                continue
            match_id = match.id
        lines_stored = 0
        try:
            for line, (over, under) in ev.lines.items():
                exists = db.scalar(select(TotalsSnapshot.id).where(
                    TotalsSnapshot.match_id == match_id, TotalsSnapshot.bookmaker == REFERENCE_BOOKMAKER,
                    TotalsSnapshot.taken_at == taken_at, TotalsSnapshot.line == line))
                if exists:
                    continue
                db.add(TotalsSnapshot(match_id=match_id, bookmaker=REFERENCE_BOOKMAKER, taken_at=taken_at, line=line, over=over, under=under))
                lines_stored += 1
            db.commit()
            report.matched += 1
            report.totals += lines_stored
        except IntegrityError:
            db.rollback()
            log.warning("conflit d'unicité odds_api totals ignoré (%s v %s)", ev.home, ev.away)
    return report


def fetch_sport(sport_key: str) -> list:
    """1 crédit par région → 2 crédits par compétition et par relevé (h2h, régions fr+eu)."""
    resp = requests.get(f"{BASE}/{sport_key}/odds",
                        params={"apiKey": settings.the_odds_api_key, "regions": "fr,eu", "markets": "h2h", "oddsFormat": "decimal"}, timeout=30)
    resp.raise_for_status()
    remaining = resp.headers.get("x-requests-remaining")
    log.info("odds_api %s : %s événements, crédits restants %s", sport_key, len(resp.json()), remaining)
    return resp.json()


def fetch_totals(sport_key: str) -> tuple[list, str | None]:
    """1 crédit (région `eu` = Pinnacle seul) → 3e crédit par compétition et par relevé, marché `totals`."""
    resp = requests.get(f"{BASE}/{sport_key}/odds",
                        params={"apiKey": settings.the_odds_api_key, "regions": "eu", "markets": "totals", "oddsFormat": "decimal"}, timeout=30)
    resp.raise_for_status()
    return resp.json(), resp.headers.get("x-requests-remaining")


def run(db: Session) -> StoreReport:
    """Un relevé complet = 7 compétitions × 3 crédits (2 h2h + 1 totals) = 21 crédits. L'horodatage est arrondi
    à l'heure, commun au relevé h2h et au relevé totals de ce passage."""
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
        for k in ("snapshots", "matched", "quarantined"):
            setattr(total, k, getattr(total, k) + getattr(r, k))

        try:
            totals_payload, remaining = fetch_totals(comp.odds_api_key)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                log.error("odds_api : quota épuisé ou clé invalide, arrêt propre du relevé (totals)")
                break
            raise
        tr = store_totals(db, parse_totals(comp.odds_api_key, totals_payload), taken_at, r.event_matches)
        log.info("totals: %s lignes, crédits restants %s", tr.totals, remaining)
        total.totals += tr.totals
    log.info("odds_api relevé %s : %s", taken_at.isoformat(), total)
    return total
