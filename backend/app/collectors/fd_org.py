"""football-data.org (plan gratuit) : calendrier, heures exactes, résultats, reports, Ligue des Champions."""
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS, by_fd_org_code
from app.collectors.fd_uk import ImportReport
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match

log = logging.getLogger("rushplay.collectors.fd_org")
BASE = "https://api.football-data.org/v4"

STATUS_MAP = {
    "SCHEDULED": MatchStatus.SCHEDULED, "TIMED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE, "PAUSED": MatchStatus.LIVE,
    "FINISHED": MatchStatus.FINISHED, "AWARDED": MatchStatus.FINISHED,
    "POSTPONED": MatchStatus.POSTPONED, "SUSPENDED": MatchStatus.POSTPONED, "CANCELLED": MatchStatus.POSTPONED,
}


@dataclass
class FdOrgMatch:
    ext_id: str
    competition_code: str
    utc_date: datetime
    home: str
    away: str
    status: str
    hg: int | None
    ag: int | None


def parse_matches(payload: dict) -> list[FdOrgMatch]:
    comp = by_fd_org_code(payload["competition"]["code"])
    if comp is None:
        return []
    out = []
    for m in payload.get("matches", []):
        try:
            ft = (m.get("score") or {}).get("fullTime") or {}
            out.append(FdOrgMatch(
                ext_id=f"fdo:{m['id']}", competition_code=comp.code,
                utc_date=datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")),
                home=m["homeTeam"]["name"], away=m["awayTeam"]["name"], status=m["status"],
                hg=ft.get("home"), ag=ft.get("away"),
            ))
        except (ValueError, KeyError, TypeError) as e:
            log.warning("match fd_org ignoré (id=%s) : %s", m.get("id"), e)
    return out


def import_matches(db: Session, items: list[FdOrgMatch]) -> ImportReport:
    report = ImportReport()
    for it in items:
        comp = COMPETITIONS[it.competition_code]
        match = db.scalar(select(Match).where(Match.external_id == it.ext_id))
        try:
            home, away = resolve_team(db, "fd_org", it.home), resolve_team(db, "fd_org", it.away)
        except TeamAliasError as e:
            log.warning("quarantaine fd_org %s : %s", it.ext_id, e)
            if match is None:
                db.add(Match(external_id=it.ext_id, competition=comp.code, league=comp.name, country=comp.country,
                             home_team=it.home, away_team=it.away, kickoff_at=it.utc_date, status=MatchStatus.QUARANTINE))
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    log.warning("conflit d'unicité fd_org ignoré (quarantaine %s)", it.ext_id)
            report.quarantined += 1
            continue
        if match is None:
            day = it.utc_date.date()
            day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
            day_end = datetime.combine(day, time.max, tzinfo=timezone.utc)
            match = db.scalar(select(Match).where(Match.competition == comp.code, Match.home_team_id == home.id,
                                                  Match.away_team_id == away.id, Match.kickoff_at >= day_start, Match.kickoff_at <= day_end))
        created = updated = 0
        try:
            if match is None:
                match = Match(external_id=it.ext_id, competition=comp.code, league=comp.name, country=comp.country,
                              home_team_id=home.id, away_team_id=away.id, home_team=home.name, away_team=away.name,
                              kickoff_at=it.utc_date)
                db.add(match); created = 1
            else:
                match.external_id = match.external_id or it.ext_id
                match.kickoff_at = it.utc_date
                match.home_team_id, match.away_team_id = home.id, away.id
                match.home_team, match.away_team = home.name, away.name
                updated = 1
            new_status = STATUS_MAP.get(it.status, MatchStatus.SCHEDULED)
            if match.status != MatchStatus.FINISHED or new_status == MatchStatus.FINISHED:
                match.status = new_status
            if new_status == MatchStatus.FINISHED and it.hg is not None:
                match.home_score, match.away_score = it.hg, it.ag
            db.flush()
            db.commit()
            report.created += created
            report.updated += updated
        except IntegrityError:
            db.rollback()
            log.warning("conflit d'unicité fd_org ignoré (%s)", it.ext_id)
    return report


def fetch(competition_code: str, date_from: date, date_to: date) -> dict:
    comp = COMPETITIONS[competition_code]
    headers = {"X-Auth-Token": settings.football_data_org_key or ""}
    resp = requests.get(f"{BASE}/competitions/{comp.fd_org_code}/matches",
                        params={"dateFrom": date_from.isoformat(), "dateTo": date_to.isoformat()}, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def run(db: Session, days_ahead: int = 10, days_back: int = 3) -> ImportReport:
    """Un appel par compétition dont le calendrier est dans le plan gratuit (fd_org_free=True) ;
    la Ligue Europa (EL) n'y est pas et est sautée. Plan gratuit = 10/min : dormir 7 s entre deux appels."""
    import time as _time
    total = ImportReport()
    today = datetime.now(timezone.utc).date()
    for code, comp in COMPETITIONS.items():
        if not comp.fd_org_free:
            continue
        payload = fetch(code, today - timedelta(days=days_back), today + timedelta(days=days_ahead))
        r = import_matches(db, parse_matches(payload))
        total.created += r.created; total.updated += r.updated; total.quarantined += r.quarantined
        log.info("fd_org %s : %s", code, r)
        _time.sleep(7)
    return total
