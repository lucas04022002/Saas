"""
Politique de sélection d'outcome (home/draw/away) configurable par ligue.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any

DRAW_THRESHOLDS_FILE = "draw_thresholds_by_league.json"

DEFAULT_THRESHOLDS = {
    "draw_prob_min": 25.0,
    "draw_balance_max": 10.0,
    "draw_margin_to_best": 5.0,
}


def _to_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def load_thresholds_map(path: str = DRAW_THRESHOLDS_FILE) -> dict[str, Any]:
    """Charge la configuration de seuils par ligue."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def get_thresholds_for_league(
    league_id: int | str | None = None,
    league_name: str | None = None,
    thresholds_map: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Retourne les seuils à appliquer pour une ligue donnée."""
    cfg = thresholds_map if thresholds_map is not None else load_thresholds_map()

    merged_default = {
        **DEFAULT_THRESHOLDS,
        **(cfg.get("default", {}) if isinstance(cfg, dict) else {}),
    }

    leagues_cfg = cfg.get("leagues", {}) if isinstance(cfg, dict) else {}
    candidate = None

    if league_id is not None:
        candidate = leagues_cfg.get(str(league_id))

    if candidate is None and league_name:
        candidate = leagues_cfg.get(league_name)
        if candidate is None:
            normalized = league_name.strip().lower()
            for key, value in leagues_cfg.items():
                if isinstance(key, str) and key.strip().lower() == normalized:
                    candidate = value
                    break

    if not isinstance(candidate, dict):
        candidate = {}

    return {
        "draw_prob_min": _to_float(candidate.get("draw_prob_min"), merged_default["draw_prob_min"]),
        "draw_balance_max": _to_float(candidate.get("draw_balance_max"), merged_default["draw_balance_max"]),
        "draw_margin_to_best": _to_float(candidate.get("draw_margin_to_best"), merged_default["draw_margin_to_best"]),
    }


def select_recommended_outcome(
    prob_model: dict[str, float],
    home_team: str,
    away_team: str,
    league_id: int | str | None = None,
    league_name: str | None = None,
    thresholds_map: dict[str, Any] | None = None,
) -> tuple[str, str, float]:
    """
    Retourne (outcome, label, probability_pct) selon les probabilités modèle.
    """
    home_prob = _to_float(prob_model.get("home"), 0.0) * 100
    draw_prob = _to_float(prob_model.get("draw"), 0.0) * 100
    away_prob = _to_float(prob_model.get("away"), 0.0) * 100

    thresholds = get_thresholds_for_league(
        league_id=league_id,
        league_name=league_name,
        thresholds_map=thresholds_map,
    )

    best_non_draw = max(home_prob, away_prob)
    if (
        draw_prob >= thresholds["draw_prob_min"]
        and abs(home_prob - away_prob) <= thresholds["draw_balance_max"]
        and draw_prob >= best_non_draw - thresholds["draw_margin_to_best"]
    ):
        return "draw", "Match Nul", draw_prob

    if home_prob >= away_prob:
        return "home", home_team, home_prob
    return "away", away_team, away_prob


def build_default_thresholds_config() -> dict[str, Any]:
    """Structure de config standard (utile pour initialisation)."""
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "default": dict(DEFAULT_THRESHOLDS),
        "leagues": {},
    }

