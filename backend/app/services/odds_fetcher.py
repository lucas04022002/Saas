"""
Fetch pre-match 1X2 odds from The Odds API (api.the-odds-api.com).
Returns a dict mapping external fixture_id (str) -> {"home": float, "draw": float, "away": float}.
Matching is done by normalizing team names since The Odds API uses different IDs.
"""
from __future__ import annotations

import logging
import unicodedata
from typing import Any

import requests

log = logging.getLogger("rushplay.odds")

_BASE_URL = "https://api.the-odds-api.com/v4/sports"

# The Odds API sport keys for our configured leagues
_SPORT_KEYS = [
    "soccer_epl",
    "soccer_france_ligue_one",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_uefa_champs_league",
]


def _normalize(name: str) -> str:
    """Lowercase, strip accents, collapse spaces."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_str.lower().strip().split())


def fetch_upcoming_odds(api_key: str, next_days: int = 7) -> dict[str, dict[str, float]]:
    """
    Return {fixture_id: {"home": x, "draw": x, "away": x}} keyed by API-Football external_id.
    Since The Odds API doesn't use the same IDs, we build a team-name index and match
    fixtures from the caller's match list at query time via fetch_odds_for_matches().
    This function returns a name-based index instead.
    """
    raise NotImplementedError("Use fetch_odds_for_matches() instead")


def fetch_odds_for_matches(
    api_key: str,
    matches: list[Any],
) -> dict[str, dict[str, float]]:
    """
    Fetch odds from The Odds API for all sports, then match against our fixtures
    by normalized team names.

    matches: list of Match ORM objects with .external_id, .home_team, .away_team
    Returns: {external_id: {"home": float, "draw": float, "away": float}}
    """
    # Build index of all events from The Odds API: (norm_home, norm_away) -> odds
    events_index: dict[tuple[str, str], dict[str, float]] = {}

    for sport_key in _SPORT_KEYS:
        try:
            events = _fetch_sport_odds(api_key, sport_key)
            for event in events:
                norm_home = _normalize(event["home_team"])
                norm_away = _normalize(event["away_team"])
                odds = _extract_h2h_odds(event, event["home_team"], event["away_team"])
                if odds:
                    events_index[(norm_home, norm_away)] = odds
        except Exception as exc:
            log.warning("Odds fetch failed for sport %s: %s", sport_key, exc)

    log.info("Odds API: indexed %d events across %d sports", len(events_index), len(_SPORT_KEYS))

    # Match our fixtures by normalized team names
    result: dict[str, dict[str, float]] = {}
    for match in matches:
        if not match.external_id:
            continue
        key = (_normalize(match.home_team), _normalize(match.away_team))
        odds = events_index.get(key)
        if odds:
            result[match.external_id] = odds

    log.info("Odds matched for %d/%d fixtures", len(result), len(matches))
    return result


def _fetch_sport_odds(api_key: str, sport_key: str) -> list[dict[str, Any]]:
    resp = requests.get(
        f"{_BASE_URL}/{sport_key}/odds/",
        params={
            "apiKey": api_key,
            "regions": "eu",
            "markets": "h2h",
            "dateFormat": "iso",
            "oddsFormat": "decimal",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _extract_h2h_odds(
    event: dict[str, Any],
    home_team: str,
    away_team: str,
) -> dict[str, float] | None:
    """Average h2h odds across bookmakers. Returns {"home", "draw", "away"} or None."""
    totals: dict[str, list[float]] = {"home": [], "draw": [], "away": []}

    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                name = outcome.get("name", "")
                price = float(outcome.get("price", 0))
                if price <= 1.0:
                    continue
                if name == "Draw":
                    totals["draw"].append(price)
                elif name == home_team:
                    totals["home"].append(price)
                elif name == away_team:
                    totals["away"].append(price)

    if not totals["home"] or not totals["away"]:
        return None

    result = {
        "home": round(sum(totals["home"]) / len(totals["home"]), 2),
        "away": round(sum(totals["away"]) / len(totals["away"]), 2),
    }
    if totals["draw"]:
        result["draw"] = round(sum(totals["draw"]) / len(totals["draw"]), 2)

    return result
