import os
import sys
import tempfile
import json

import pytest

# Résolution du chemin vers prediction_engine.py
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import EloRating


@pytest.fixture
def elo(tmp_path):
    e = EloRating(home_advantage=100, initial_rating=1500)
    e.history_file = str(tmp_path / "elo_test.json")
    e.ratings = {}
    e.matches_played = {}
    e.last_decay_season = None  # Isoler des fichiers existants (ex. après training)
    return e


# ── K-factor dynamique ──────────────────────────────────────────────────────

def test_k_factor_new_team_is_40(elo):
    assert elo._get_k_factor("NewTeam") == 40


def test_k_factor_after_10_matches_is_32(elo):
    elo.matches_played["SomeTeam"] = 10
    assert elo._get_k_factor("SomeTeam") == 32


def test_k_factor_after_30_matches_is_24(elo):
    elo.matches_played["OldTeam"] = 30
    assert elo._get_k_factor("OldTeam") == 24


def test_k_factor_decreases_over_time(elo):
    elo.matches_played["Team"] = 0
    k0 = elo._get_k_factor("Team")
    elo.matches_played["Team"] = 10
    k10 = elo._get_k_factor("Team")
    elo.matches_played["Team"] = 30
    k30 = elo._get_k_factor("Team")
    assert k0 > k10 > k30


# ── Mise à jour des ratings ─────────────────────────────────────────────────

def test_winner_rating_increases(elo):
    before = elo.get_rating("Home")
    elo.update_ratings("Home", "Away", 2, 0)
    assert elo.get_rating("Home") > before


def test_loser_rating_decreases(elo):
    before = elo.get_rating("Away")
    elo.update_ratings("Home", "Away", 2, 0)
    assert elo.get_rating("Away") < before


def test_matches_played_incremented(elo):
    elo.update_ratings("Home", "Away", 1, 0)
    assert elo.matches_played["Home"] == 1
    assert elo.matches_played["Away"] == 1
    elo.update_ratings("Home", "Away", 0, 1)
    assert elo.matches_played["Home"] == 2
    assert elo.matches_played["Away"] == 2


def test_new_team_moves_more_than_established(elo):
    """Une nouvelle équipe (K=40) doit bouger plus qu'une équipe à K=24."""
    elo.matches_played["Established"] = 50
    rating_before_new = elo.get_rating("NewTeam")
    rating_before_est = elo.get_rating("Established")

    elo.update_ratings("NewTeam", "Opponent1", 2, 0)
    elo.update_ratings("Established", "Opponent2", 2, 0)

    delta_new = elo.get_rating("NewTeam") - rating_before_new
    delta_est = elo.get_rating("Established") - rating_before_est
    assert delta_new > delta_est


# ── Persistance ─────────────────────────────────────────────────────────────

def test_save_and_load_preserves_matches_played(elo):
    elo.update_ratings("PSG", "OM", 3, 0)
    elo.save_ratings()

    elo2 = EloRating()
    elo2.history_file = elo.history_file
    elo2.load_ratings()

    assert elo2.matches_played.get("PSG") == 1
    assert abs(elo2.get_rating("PSG") - elo.get_rating("PSG")) < 0.01


def test_load_old_format_migrates_gracefully(elo, tmp_path):
    """L'ancien format plat {team: rating} doit être lu sans erreur."""
    old_file = tmp_path / "old_elo.json"
    old_file.write_text(json.dumps({"PSG": 1600, "OM": 1450}))

    elo.history_file = str(old_file)
    elo.load_ratings()

    assert elo.get_rating("PSG") == 1600
    assert elo.matches_played == {}  # pas de compteurs dans l'ancien format


# ── Seasonal decay ──────────────────────────────────────────────────────────

def test_decay_moves_rating_toward_mean(elo):
    elo.ratings["PSG"] = 1700
    elo.apply_season_decay(season=2025)
    assert 1500 < elo.get_rating("PSG") < 1700


def test_decay_below_mean_moves_up(elo):
    elo.ratings["Metz"] = 1300
    elo.apply_season_decay(season=2025)
    assert 1300 < elo.get_rating("Metz") < 1500


def test_decay_20_percent_formula(elo):
    elo.ratings["Team"] = 1700
    elo.apply_season_decay(season=2025, decay=0.2)
    expected = 1700 * 0.8 + 1500 * 0.2
    assert abs(elo.get_rating("Team") - expected) < 0.01


def test_decay_not_applied_twice_same_season(elo):
    elo.ratings["Team"] = 1700
    elo.apply_season_decay(season=2025)
    rating_after_first = elo.get_rating("Team")
    elo.apply_season_decay(season=2025)  # doit être ignoré
    assert elo.get_rating("Team") == rating_after_first


def test_decay_applied_each_new_season(elo):
    elo.ratings["Team"] = 1700
    elo.apply_season_decay(season=2024)
    after_2024 = elo.get_rating("Team")
    elo.apply_season_decay(season=2025)
    after_2025 = elo.get_rating("Team")
    assert after_2025 < after_2024  # régresse encore vers 1500


def test_decay_halves_matches_played(elo):
    elo.matches_played["Team"] = 40
    elo.apply_season_decay(season=2025)
    assert elo.matches_played["Team"] == 20


def test_decay_returns_affected_count(elo):
    elo.ratings = {"PSG": 1700, "OM": 1600, "Lyon": 1550}
    n = elo.apply_season_decay(season=2025)
    assert n == 3


def test_decay_returns_zero_if_already_applied(elo):
    elo.ratings["PSG"] = 1700
    elo.apply_season_decay(season=2025)
    n = elo.apply_season_decay(season=2025)
    assert n == 0


def test_decay_persisted_in_save_load(elo):
    elo.ratings["PSG"] = 1700
    elo.apply_season_decay(season=2025)
    elo.save_ratings()

    elo2 = EloRating()
    elo2.history_file = elo.history_file
    elo2.load_ratings()

    assert elo2.last_decay_season == 2025
    # Decay ne doit pas se ré-appliquer après reload
    n = elo2.apply_season_decay(season=2025)
    assert n == 0
