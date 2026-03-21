"""
Imports upcoming fixtures from API-Football into the matches table.
Uses UPSERT on external_id so re-runs are idempotent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MatchStatus
from app.models.match import Match

API_HOST = "v3.football.api-sports.io"
API_BASE = f"https://{API_HOST}"

# league_id → (league_display_name, country)
LEAGUES: dict[int, tuple[str, str]] = {
    39:  ("Premier League (Ang)", "England"),
    61:  ("Ligue 1 (Fra)",        "France"),
    140: ("La Liga (Esp)",        "Spain"),
    78:  ("Bundesliga (All)",     "Germany"),
    135: ("Serie A (Ita)",        "Italy"),
    2:   ("Ligue des Champions",  "Europe"),
}


def _current_season(league_id: int) -> int:
    now = datetime.now(timezone.utc)
    # UCL season key = year the season started (e.g. 2025 for 2025-26)
    if league_id == 2:
        return now.year - 1 if now.month < 7 else now.year
    return now.year if now.month >= 7 else now.year - 1


def _fetch_fixtures(api_key: str, league_id: int, season: int, next_days: int = 7) -> list[dict[str, Any]]:
    headers = {
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": api_key,
    }
    params = {
        "league": league_id,
        "season": season,
        "next": next_days,
    }
    resp = requests.get(f"{API_BASE}/fixtures", headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(f"API-Football error for league {league_id}: {data['errors']}")
    return data.get("response", [])


def import_upcoming_matches(db: Session, api_key: str, next_days: int = 7) -> dict[str, int]:
    """
    Fetch upcoming fixtures for all configured leagues and upsert into DB.
    Returns a summary dict with created/updated/skipped counts.
    """
    summary = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    for league_id, (league_name, country) in LEAGUES.items():
        season = _current_season(league_id)
        try:
            fixtures = _fetch_fixtures(api_key, league_id, season, next_days)
        except Exception as exc:
            summary["errors"] += 1
            continue

        for fixture in fixtures:
            try:
                _upsert_fixture(db, fixture, league_name, country, summary)
            except Exception:
                summary["errors"] += 1

    db.commit()
    return summary


def _upsert_fixture(
    db: Session,
    fixture: dict[str, Any],
    league_name: str,
    country: str,
    summary: dict[str, int],
) -> None:
    f = fixture.get("fixture", {})
    teams = fixture.get("teams", {})
    external_id = str(f.get("id", ""))
    home_team = teams.get("home", {}).get("name", "")
    away_team = teams.get("away", {}).get("name", "")
    date_str: str = f.get("date", "")

    if not external_id or not home_team or not away_team or not date_str:
        summary["skipped"] += 1
        return

    kickoff_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    # Check status from API
    api_status = f.get("status", {}).get("short", "NS")
    if api_status in ("FT", "AET", "PEN"):
        db_status = MatchStatus.FINISHED
    elif api_status in ("1H", "HT", "2H", "ET", "BT", "P", "LIVE"):
        db_status = MatchStatus.LIVE
    else:
        db_status = MatchStatus.SCHEDULED

    existing = db.scalars(select(Match).where(Match.external_id == external_id)).first()

    if existing:
        existing.home_team = home_team
        existing.away_team = away_team
        existing.kickoff_at = kickoff_at
        existing.status = db_status
        summary["updated"] += 1
    else:
        db.add(
            Match(
                external_id=external_id,
                home_team=home_team,
                away_team=away_team,
                league=league_name,
                country=country,
                kickoff_at=kickoff_at,
                status=db_status,
            )
        )
        summary["created"] += 1
