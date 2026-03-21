import sys
import json
import pytest
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from stats_collector import (
    parse_fixture_stats, load_stats_cache, save_stats_cache,
    build_rolling_stats_index, get_rolling_stats,
)
from prediction_engine import XGBoostPredictor


# ── parse_fixture_stats ───────────────────────────────────────────────────────

def _make_response(home_xg, away_xg, home_poss=55, away_poss=45,
                   home_sog=5, away_sog=3, home_ts=14, away_ts=9):
    """Construit une réponse API factice."""
    def stats(xg, poss, sog, ts):
        return [
            {'type': 'expected_goals',  'value': str(xg)},
            {'type': 'Ball Possession', 'value': f'{poss}%'},
            {'type': 'Shots on Goal',   'value': sog},
            {'type': 'Total Shots',     'value': ts},
        ]
    return [
        {'team': {'id': 1, 'name': 'Home'}, 'statistics': stats(home_xg, home_poss, home_sog, home_ts)},
        {'team': {'id': 2, 'name': 'Away'}, 'statistics': stats(away_xg, away_poss, away_sog, away_ts)},
    ]


def test_parse_returns_home_and_away():
    result = parse_fixture_stats(_make_response(1.5, 0.8))
    assert 'home' in result and 'away' in result


def test_parse_xg_values():
    result = parse_fixture_stats(_make_response(1.5, 0.8))
    assert abs(result['home']['xg'] - 1.5) < 1e-6
    assert abs(result['away']['xg'] - 0.8) < 1e-6


def test_parse_possession_strips_percent():
    result = parse_fixture_stats(_make_response(1.0, 1.0, home_poss=60, away_poss=40))
    assert result['home']['possession'] == 60.0
    assert result['away']['possession'] == 40.0


def test_parse_empty_response_returns_none():
    assert parse_fixture_stats([]) is None


def test_parse_single_team_returns_none():
    result = parse_fixture_stats(_make_response(1.0, 1.0)[:1])
    assert result is None


# ── Cache load/save ───────────────────────────────────────────────────────────

def test_load_missing_cache_returns_empty(tmp_path):
    cache = load_stats_cache(str(tmp_path / "missing.json"))
    assert cache == {}


def test_save_and_reload_cache(tmp_path):
    path = str(tmp_path / "cache.json")
    data = {"123": {"home": {"xg": 1.5}, "away": {"xg": 0.8}}}
    save_stats_cache(data, path)
    loaded = load_stats_cache(path)
    assert loaded["123"]["home"]["xg"] == 1.5


# ── build_rolling_stats_index ─────────────────────────────────────────────────

def _make_fixture(fid, home, away):
    return {
        'fixture': {'id': fid, 'date': '2025-01-01', 'status': {'short': 'FT'}},
        'teams': {'home': {'name': home}, 'away': {'name': away}},
        'score': {'fulltime': {'home': 1, 'away': 0}},
    }


def test_first_fixture_snapshot_is_empty():
    fixtures = [_make_fixture(1, 'PSG', 'OM')]
    cache = {"1": {"home": {"xg": 2.0, "shots_on_goal": 6, "total_shots": 15, "possession": 60},
                   "away": {"xg": 0.5, "shots_on_goal": 2, "total_shots": 7,  "possession": 40}}}
    snapshots = build_rolling_stats_index(fixtures, cache, n=5)
    # Premier snapshot : aucun historique encore
    assert get_rolling_stats(snapshots[0], 'PSG') is None


def test_second_fixture_has_first_match_stats():
    fixtures = [
        _make_fixture(1, 'PSG', 'OM'),
        _make_fixture(2, 'PSG', 'Lyon'),
    ]
    stats_1 = {"xg": 2.0, "shots_on_goal": 6, "total_shots": 15, "possession": 60.0}
    cache = {
        "1": {"home": stats_1, "away": {"xg": 0.5, "shots_on_goal": 2, "total_shots": 7, "possession": 40.0}},
    }
    snapshots = build_rolling_stats_index(fixtures, cache, n=5)
    stats = get_rolling_stats(snapshots[1], 'PSG')
    assert stats is not None
    assert abs(stats['xg'] - 2.0) < 1e-6


def test_rolling_window_averages_correctly():
    """Après 3 matchs avec xG 1.0, 2.0, 3.0 → moyenne = 2.0."""
    fixtures = [_make_fixture(i, 'PSG', 'Other') for i in range(1, 5)]
    cache = {
        "1": {"home": {"xg": 1.0, "shots_on_goal": 4, "total_shots": 10, "possession": 50.0}, "away": {"xg": 1.0, "shots_on_goal": 4, "total_shots": 10, "possession": 50.0}},
        "2": {"home": {"xg": 2.0, "shots_on_goal": 4, "total_shots": 10, "possession": 50.0}, "away": {"xg": 1.0, "shots_on_goal": 4, "total_shots": 10, "possession": 50.0}},
        "3": {"home": {"xg": 3.0, "shots_on_goal": 4, "total_shots": 10, "possession": 50.0}, "away": {"xg": 1.0, "shots_on_goal": 4, "total_shots": 10, "possession": 50.0}},
    }
    snapshots = build_rolling_stats_index(fixtures, cache, n=5)
    stats = get_rolling_stats(snapshots[3], 'PSG')
    assert abs(stats['xg'] - 2.0) < 1e-6


# ── Intégration avec create_features ─────────────────────────────────────────

def test_create_features_with_stats_size():
    xgb = XGBoostPredictor()
    match_stats = {"xg": 1.8, "shots_on_goal": 5, "total_shots": 13, "possession": 58.0}
    feat = xgb.create_features(
        "PSG", "OM",
        {"PSG": 1700, "OM": 1550},
        {"PSG": {"attack": 1.8, "defense": 1.0}, "OM": {"attack": 1.2, "defense": 1.4}},
        home_match_stats=match_stats,
        away_match_stats={"xg": 0.9, "shots_on_goal": 3, "total_shots": 8, "possession": 42.0},
    )
    assert feat.shape == (1, 57)


def test_create_features_without_stats_uses_defaults():
    """Sans stats → valeurs par défaut, taille 57 inchangée."""
    xgb = XGBoostPredictor()
    feat = xgb.create_features(
        "A", "B",
        {"A": 1500, "B": 1500},
        {"A": {"attack": 1.25, "defense": 1.25}, "B": {"attack": 1.25, "defense": 1.25}},
    )
    assert feat.shape == (1, 57)
    # Les features stats (indices 47-56) doivent être les valeurs par défaut
    assert feat[0, 47] == 1.25   # home xg
    assert feat[0, 51] == 1.25   # away xg
    assert feat[0, 55] == 0.0    # xg_diff = 0
    assert feat[0, 56] == 0.0    # shots_diff = 0
