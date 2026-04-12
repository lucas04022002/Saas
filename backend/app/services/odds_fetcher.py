"""
Fetch pre-match 1X2 odds from API-Football for upcoming fixtures.
Returns a dict mapping external fixture_id (str) -> {"home": float, "draw": float, "away": float}.
Falls back gracefully — callers receive an empty dict on failure.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from app.services.match_importer import API_BASE, API_HOST, LEAGUES, _current_season

log = logging.getLogger("rushplay.odds")

_BET_ID = 1  # "Match Winner" in API-Football bets catalogue


def fetch_upcoming_odds(api_key: str, next_days: int = 7) -> dict[str, dict[str, float]]:
    """Return {fixture_id: {"home": x, "draw": x, "away": x}} for all configured leagues."""
    result: dict[str, dict[str, float]] = {}
    for league_id in LEAGUES:
        season = _current_season(league_id)
        try:
            league_odds = _fetch_league_odds(api_key, league_id, season, next_days)
            result.update(league_odds)
        except Exception as exc:
            log.warning("Odds fetch failed for league %d: %s", league_id, exc)
    return result


def _fetch_league_odds(
    api_key: str, league_id: int, season: int, next_days: int
) -> dict[str, dict[str, float]]:
    resp = requests.get(
        f"{API_BASE}/odds",
        headers={"x-rapidapi-host": API_HOST, "x-rapidapi-key": api_key},
        params={"league": league_id, "season": season, "next": next_days, "bet": _BET_ID},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    result: dict[str, dict[str, float]] = {}
    for item in data.get("response", []):
        fixture_id = str(item.get("fixture", {}).get("id", ""))
        if not fixture_id:
            continue
        odds = _extract_1x2_odds(item.get("bookmakers", []))
        if odds:
            result[fixture_id] = odds
    return result


def _extract_1x2_odds(bookmakers: list[dict[str, Any]]) -> dict[str, float] | None:
    """Average 1X2 odds across all bookmakers for robustness."""
    totals: dict[str, list[float]] = {"home": [], "draw": [], "away": []}
    label_map = {"Home": "home", "Draw": "draw", "Away": "away"}

    for bookmaker in bookmakers:
        for bet in bookmaker.get("bets", []):
            if bet.get("id") != _BET_ID:
                continue
            for value in bet.get("values", []):
                key = label_map.get(value.get("value", ""))
                if key:
                    try:
                        totals[key].append(float(value["odd"]))
                    except (KeyError, ValueError):
                        pass

    if not totals["home"] or not totals["draw"] or not totals["away"]:
        return None

    return {
        "home": round(sum(totals["home"]) / len(totals["home"]), 2),
        "draw": round(sum(totals["draw"]) / len(totals["draw"]), 2),
        "away": round(sum(totals["away"]) / len(totals["away"]), 2),
    }
