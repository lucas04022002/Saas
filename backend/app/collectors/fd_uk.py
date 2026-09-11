"""football-data.co.uk : résultats, tirs et cotes d'ouverture/clôture (CSV par saison et championnat).

Convention horaire : l'heure de la colonne `Time` est l'heure locale UK (Europe/London, donc BST l'été = UTC+1,
GMT l'hiver = UTC+0) ; elle est convertie en UTC via zoneinfo avant stockage. À défaut d'heure, le coup d'envoi
retombe directement sur 15:00 UTC (aucune conversion de fuseau appliquée dans ce cas — comportement inchangé).
Convention des cotes : l'instantané d'ouverture est daté J−7 12:00 UTC et celui de clôture sur le coup d'envoi
dérivé de la ligne CSV (`_kickoff(r.date, r.time)`, jamais `match.kickoff_at`) moins 1h, pour rester dans la
fenêtre `taken_at <= kickoff_at` attendue en aval même quand fd_org corrige ensuite l'horaire du match.
"""
import csv
import io
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS
from app.collectors.dedup import find_existing, merge_matches
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot

log = logging.getLogger("rushplay.collectors.fd_uk")
UK_TZ = ZoneInfo("Europe/London")


@dataclass
class FdUkRow:
    date: date
    home: str
    away: str
    hg: int
    ag: int
    time: time | None
    hs: int | None
    as_: int | None
    avg_open: tuple[float, float, float] | None
    avg_close: tuple[float, float, float] | None
    ps_open: tuple[float, float, float] | None
    ps_close: tuple[float, float, float] | None


@dataclass
class FixtureRow:
    div: str
    date: date
    time: time | None
    home: str
    away: str
    avg: tuple[float, float, float] | None
    max_: tuple[float, float, float] | None


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    quarantined: int = 0
    snapshots: int = 0


FIXTURE_DIVS = {c.fd_uk_code for c in COMPETITIONS.values() if c.fd_uk_code}   # {"E0", "F1", "SP1", "D1", "I1"}


def _f(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def _i(v: str | None) -> int | None:
    try:
        return int(v) if v not in (None, "") else None
    except ValueError:
        return None


def _triple(r: dict, h: str, d: str, a: str) -> tuple[float, float, float] | None:
    vals = (_f(r.get(h)), _f(r.get(d)), _f(r.get(a)))
    return None if any(v is None for v in vals) else vals  # type: ignore[return-value]


def parse_csv(text: str) -> list[FdUkRow]:
    rows = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        if not r.get("Date") or not r.get("FTR"):
            continue
        try:
            d, m, y = r["Date"].split("/")
            year = int(y) if len(y) == 4 else 2000 + int(y)
            t = None
            time_str = (r.get("Time") or "").strip()
            if time_str:
                hh, mm = time_str.split(":")
                t = time(int(hh), int(mm))
            rows.append(FdUkRow(
                date=date(year, int(m), int(d)), home=r["HomeTeam"].strip(), away=r["AwayTeam"].strip(),
                hg=int(r["FTHG"]), ag=int(r["FTAG"]), time=t, hs=_i(r.get("HS")), as_=_i(r.get("AS")),
                avg_open=_triple(r, "AvgH", "AvgD", "AvgA"), avg_close=_triple(r, "AvgCH", "AvgCD", "AvgCA"),
                ps_open=_triple(r, "PSH", "PSD", "PSA"), ps_close=_triple(r, "PSCH", "PSCD", "PSCA"),
            ))
        except (ValueError, KeyError, TypeError) as e:
            log.warning("ligne fd_uk ignorée (%s vs %s, Date=%r) : %s", r.get("HomeTeam"), r.get("AwayTeam"), r.get("Date"), e)
    return rows


def parse_fixtures_csv(text: str) -> list[FixtureRow]:
    """fixtures.csv : matchs à venir toutes compétitions confondues, sans score. On ne garde que les 5 championnats
    fd_uk connus (COMPETITIONS[*].fd_uk_code) ; les autres divisions (E1, SC0, ...) sont ignorées."""
    rows = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        div = (r.get("Div") or "").strip()
        if div not in FIXTURE_DIVS:
            continue
        if not r.get("Date") or not r.get("HomeTeam") or not r.get("AwayTeam"):
            continue
        try:
            d, m, y = r["Date"].split("/")
            year = int(y) if len(y) == 4 else 2000 + int(y)
            t = None
            time_str = (r.get("Time") or "").strip()
            if time_str:
                hh, mm = time_str.split(":")
                t = time(int(hh), int(mm))
            rows.append(FixtureRow(
                div=div, date=date(year, int(m), int(d)), time=t,
                home=r["HomeTeam"].strip(), away=r["AwayTeam"].strip(),
                avg=_triple(r, "AvgH", "AvgD", "AvgA"), max_=_triple(r, "MaxH", "MaxD", "MaxA"),
            ))
        except (ValueError, KeyError, TypeError) as e:
            log.warning("ligne fixtures fd_uk ignorée (%s vs %s, Date=%r) : %s", r.get("HomeTeam"), r.get("AwayTeam"), r.get("Date"), e)
    return rows


def _kickoff(d: date, t: time | None) -> datetime:
    """Heure UK locale de la colonne `Time` (Europe/London) convertie en UTC ; à défaut d'heure, 15:00 UTC
    directement, sans conversion de fuseau (voir docstring du module)."""
    if t is None:
        return datetime.combine(d, time(15, 0), tzinfo=timezone.utc)
    return datetime.combine(d, t, tzinfo=UK_TZ).astimezone(timezone.utc)


def _add_snapshot(db: Session, match: Match, bookmaker: str, taken_at: datetime, odds: tuple[float, float, float] | None) -> int:
    if odds is None:
        return 0
    exists = db.scalar(select(OddsSnapshot.id).where(OddsSnapshot.match_id == match.id, OddsSnapshot.bookmaker == bookmaker, OddsSnapshot.taken_at == taken_at))
    if exists:
        return 0
    db.add(OddsSnapshot(match_id=match.id, bookmaker=bookmaker, taken_at=taken_at, home=odds[0], draw=odds[1], away=odds[2]))
    return 1


def import_rows(db: Session, competition_code: str, rows: list[FdUkRow]) -> ImportReport:
    comp = COMPETITIONS[competition_code]
    report = ImportReport()
    for r in rows:
        key = f"{competition_code}:{r.date.isoformat()}:{r.home}:{r.away}"
        match = db.scalar(select(Match).where(Match.fd_uk_key == key))
        try:
            home, away = resolve_team(db, "fd_uk", r.home), resolve_team(db, "fd_uk", r.away)
        except TeamAliasError as e:
            log.warning("quarantaine fd_uk %s : %s", key, e)
            if match is None:
                db.add(Match(fd_uk_key=key, competition=competition_code, league=comp.name, country=comp.country,
                             home_team=r.home, away_team=r.away, kickoff_at=_kickoff(r.date, r.time), status=MatchStatus.QUARANTINE))
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    log.warning("conflit d'unicité fd_uk ignoré (quarantaine %s)", key)
            report.quarantined += 1
            continue
        kickoff = _kickoff(r.date, r.time)
        # un match désignant les mêmes équipes/compétition, à coup d'envoi proche, a pu être créé par une autre
        # source (fd_org, odds_api) avant que ce fd_uk_key ne soit posé
        other = find_existing(db, competition_code, home.id, away.id, kickoff)
        if match is not None and match.status == MatchStatus.QUARANTINE and other is not None:
            # la quarantaine se résout sur un match déjà résolu ailleurs : une mise à jour en place entrerait en
            # conflit avec la contrainte d'unicité (compétition, kickoff, équipes) de `other` -> fusion à la place
            merge_matches(db, other, match)
            match = other
        elif match is None:
            match = other   # match déjà posé par une autre source, pas encore rapproché par fd_uk_key

        created = updated = snapshots = 0
        try:
            if match is None:
                match = Match(fd_uk_key=key, competition=competition_code, league=comp.name, country=comp.country,
                              home_team_id=home.id, away_team_id=away.id, home_team=home.name, away_team=away.name,
                              kickoff_at=kickoff)
                db.add(match); created = 1
            else:
                match.fd_uk_key = match.fd_uk_key or key
                match.home_team_id, match.away_team_id = home.id, away.id
                match.home_team, match.away_team = home.name, away.name
                updated = 1
            match.status, match.home_score, match.away_score = MatchStatus.FINISHED, r.hg, r.ag
            match.home_shots, match.away_shots = r.hs, r.as_
            db.flush()
            # cotes : ouverture datée J−7 12:00 UTC, clôture datée coup d'envoi dérivé de la ligne CSV (pas match.kickoff_at) − 1h (convention documentée dans le docstring du module)
            opening_at = datetime.combine(r.date - timedelta(days=7), time(12, 0), tzinfo=timezone.utc)
            closing_at = kickoff - timedelta(hours=1)
            snapshots += _add_snapshot(db, match, "fd_uk_avg", opening_at, r.avg_open)
            snapshots += _add_snapshot(db, match, "fd_uk_avg", closing_at, r.avg_close)
            snapshots += _add_snapshot(db, match, "fd_uk_pinnacle", opening_at, r.ps_open)
            snapshots += _add_snapshot(db, match, "fd_uk_pinnacle", closing_at, r.ps_close)
            db.commit()
            report.created += created
            report.updated += updated
            report.snapshots += snapshots
        except IntegrityError:
            db.rollback()
            log.warning("conflit d'unicité fd_uk ignoré (%s)", key)
    return report


def import_fixtures(db: Session, rows: list[FixtureRow], taken_at: datetime) -> ImportReport:
    """Importe les matchs à venir de fixtures.csv : crée/retrouve le match (SCHEDULED, jamais de score) et une
    seule cote fd_uk_avg par match, à `taken_at` arrondi à l'heure (idempotent sur match/bookmaker/taken_at)."""
    taken_at = taken_at.replace(minute=0, second=0, microsecond=0)
    report = ImportReport()
    for r in rows:
        comp = COMPETITIONS.get(r.div)
        if comp is None:
            continue
        key = f"{r.div}:{r.date.isoformat()}:{r.home}:{r.away}"
        match = db.scalar(select(Match).where(Match.fd_uk_key == key))
        try:
            home, away = resolve_team(db, "fd_uk", r.home), resolve_team(db, "fd_uk", r.away)
        except TeamAliasError as e:
            log.warning("quarantaine fixtures fd_uk %s : %s", key, e)
            if match is None:
                db.add(Match(fd_uk_key=key, competition=r.div, league=comp.name, country=comp.country,
                             home_team=r.home, away_team=r.away, kickoff_at=_kickoff(r.date, r.time), status=MatchStatus.QUARANTINE))
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    log.warning("conflit d'unicité fixtures fd_uk ignoré (quarantaine %s)", key)
            report.quarantined += 1
            continue
        kickoff = _kickoff(r.date, r.time)
        # un match déjà créé par fd_org (calendrier) ou par odds_api, pour les mêmes équipes à coup d'envoi proche
        other = find_existing(db, r.div, home.id, away.id, kickoff)
        if match is not None and match.status == MatchStatus.QUARANTINE and other is not None:
            merge_matches(db, other, match)
            match = other
        elif match is None:
            match = other

        created = updated = snapshots = 0
        try:
            if match is None:
                match = Match(fd_uk_key=key, competition=r.div, league=comp.name, country=comp.country,
                              home_team_id=home.id, away_team_id=away.id, home_team=home.name, away_team=away.name,
                              kickoff_at=kickoff, status=MatchStatus.SCHEDULED)
                db.add(match); created = 1
            else:
                match.fd_uk_key = match.fd_uk_key or key
                match.home_team_id, match.away_team_id = home.id, away.id
                match.home_team, match.away_team = home.name, away.name
                if match.status != MatchStatus.FINISHED:   # jamais de rétrogradation d'un match déjà joué
                    match.status = MatchStatus.SCHEDULED
                updated = 1
            db.flush()
            snapshots += _add_snapshot(db, match, "fd_uk_avg", taken_at, r.avg)
            db.commit()
            report.created += created
            report.updated += updated
            report.snapshots += snapshots
        except IntegrityError:
            db.rollback()
            log.warning("conflit d'unicité fixtures fd_uk ignoré (%s)", key)
    return report


def _decode_csv(resp: requests.Response) -> str:
    """football-data.co.uk n'annonce pas de charset : requests décode en ISO-8859-1 et le BOM UTF-8
    devient « ï»¿ » devant la première colonne (Div), ce qui fait ignorer toutes les lignes.
    On décode donc les octets en utf-8-sig, qui retire le BOM."""
    return resp.content.decode("utf-8-sig", errors="replace")


def fetch_fixtures() -> str:
    resp = requests.get("https://www.football-data.co.uk/fixtures.csv", timeout=30)
    resp.raise_for_status()
    return _decode_csv(resp)


def run_fixtures(db: Session) -> ImportReport:
    """Importe les matchs de la semaine (toutes compétitions) avec leurs cotes moyennes depuis fixtures.csv."""
    report = import_fixtures(db, parse_fixtures_csv(fetch_fixtures()), datetime.now(timezone.utc))
    log.info("fd_uk fixtures : %s", report)
    return report


def fetch_season(code: str, season: str) -> str:
    url = f"{settings.fd_uk_base_url}/{season}/{code}.csv"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return _decode_csv(resp)


def run(db: Session, seasons: list[str]) -> dict[str, ImportReport]:
    """Importe les saisons demandées pour les 5 championnats fd_uk. `seasons` ex. ["2425", "2526"]."""
    out: dict[str, ImportReport] = {}
    for comp in COMPETITIONS.values():
        if comp.fd_uk_code is None:
            continue
        for season in seasons:
            rows = parse_csv(fetch_season(comp.fd_uk_code, season))
            out[f"{comp.code}:{season}"] = import_rows(db, comp.code, rows)
            log.info("fd_uk %s %s : %s", comp.code, season, out[f"{comp.code}:{season}"])
    return out
