"""
Fetch last N results for a team from API-Football.
Returns a compact form string like "WWLDW" (most recent last).
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from app.services.match_importer import API_BASE, API_HOST

log = logging.getLogger("rushplay.form")


def fetch_team_form(api_key: str, team_ext_id: str, last: int = 5) -> str | None:
    """Return form string e.g. 'WDLWW' for last N results, or None on failure."""
    try:
        resp = requests.get(
            f"{API_BASE}/fixtures",
            headers={"x-rapidapi-host": API_HOST, "x-rapidapi-key": api_key},
            params={"team": team_ext_id, "last": last, "status": "FT-AET-PEN"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        fixtures = data.get("response", [])
    except Exception as exc:
        log.warning("Form fetch failed for team %s: %s", team_ext_id, exc)
        return None

    results = []
    for fx in fixtures:
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        home_id = str(teams.get("home", {}).get("id", ""))
        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            continue

        is_home = home_id == str(team_ext_id)
        team_goals = home_goals if is_home else away_goals
        opp_goals = away_goals if is_home else home_goals

        if team_goals > opp_goals:
            results.append("W")
        elif team_goals == opp_goals:
            results.append("D")
        else:
            results.append("L")

    return "".join(results) if results else None


def populate_team_stats(
    api_key: str,
    matches: list[Any],
    db: Any,
) -> None:
    """
    For each match with team ext IDs, fetch last 5 results and upsert TeamStats.
    Only processes matches that don't already have up-to-date stats.
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.enums import TeamType
    from app.models.team_stats import TeamStats

    for match in matches:
        if not match.home_team_ext_id or not match.away_team_ext_id:
            continue

        for team_ext_id, team_type in [
            (match.home_team_ext_id, TeamType.HOME),
            (match.away_team_ext_id, TeamType.AWAY),
        ]:
            form = fetch_team_form(api_key, team_ext_id)
            if not form:
                continue

            existing = db.scalar(
                select(TeamStats).where(
                    TeamStats.match_id == match.id,
                    TeamStats.team_type == team_type,
                )
            )

            if existing:
                existing.recent_form = form
                existing.updated_at = datetime.now(timezone.utc)
            else:
                db.add(
                    TeamStats(
                        match_id=match.id,
                        team_type=team_type,
                        recent_form=form,
                        goals_scored=0,
                        goals_conceded=0,
                        xg=0.0,
                        xga=0.0,
                        possession_avg=0.0,
                        shots_on_target_avg=0.0,
                        clean_sheets=0,
                    )
                )

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        log.error("Failed to commit team stats: %s", exc)
