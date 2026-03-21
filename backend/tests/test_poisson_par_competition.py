import sys
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import PoissonPredictor


@pytest.fixture
def poisson():
    return PoissonPredictor()


# ── _key helper ──────────────────────────────────────────────────────────────

def test_key_without_league(poisson):
    assert poisson._key("PSG") == "PSG"


def test_key_with_league(poisson):
    assert poisson._key("PSG", league_id=61) == "61:PSG"


# ── get_stats avec fallback ───────────────────────────────────────────────────

def test_get_stats_returns_empty_for_unknown(poisson):
    assert poisson.get_stats("Unknown") == {}


def test_get_stats_plain_key(poisson):
    poisson.team_stats["PSG"] = {"attack": 2.0, "defense": 1.0}
    assert poisson.get_stats("PSG")["attack"] == 2.0


def test_get_stats_league_key(poisson):
    poisson.team_stats["61:PSG"] = {"attack": 2.5, "defense": 0.8}
    assert poisson.get_stats("PSG", league_id=61)["attack"] == 2.5


def test_get_stats_fallback_to_plain_when_no_league_specific(poisson):
    """Si pas de clé ligue, on se rabat sur la clé sans league."""
    poisson.team_stats["PSG"] = {"attack": 1.8, "defense": 1.2}
    assert poisson.get_stats("PSG", league_id=61)["attack"] == 1.8


def test_get_stats_league_takes_priority_over_plain(poisson):
    """La clé ligue-spécifique prime sur la clé sans league."""
    poisson.team_stats["PSG"] = {"attack": 1.8, "defense": 1.2}
    poisson.team_stats["61:PSG"] = {"attack": 2.5, "defense": 0.8}
    assert poisson.get_stats("PSG", league_id=61)["attack"] == 2.5


# ── update_stats par ligue ────────────────────────────────────────────────────

def test_update_stats_without_league_uses_plain_key(poisson):
    poisson.update_stats("Arsenal", 50, 30, 20)
    assert "Arsenal" in poisson.team_stats


def test_update_stats_with_league_uses_prefixed_key(poisson):
    poisson.update_stats("Arsenal", 50, 30, 20, league_id=39)
    assert "39:Arsenal" in poisson.team_stats
    assert "Arsenal" not in poisson.team_stats


def test_update_stats_different_leagues_independent(poisson):
    """Stats PL et UCL d'une même équipe sont indépendantes."""
    poisson.update_stats("Arsenal", goals_for=60, goals_against=20, matches_played=20,
                         league_id=39)   # PL : équipe forte
    poisson.update_stats("Arsenal", goals_for=10, goals_against=20, matches_played=10,
                         league_id=2)    # UCL : équipe faible

    pl_attack  = poisson.get_stats("Arsenal", league_id=39)["attack"]
    ucl_attack = poisson.get_stats("Arsenal", league_id=2)["attack"]

    assert pl_attack > ucl_attack


def test_update_stats_no_effect_if_zero_matches(poisson):
    poisson.update_stats("Team", 10, 5, 0)
    assert "Team" not in poisson.team_stats


# ── get_expected_goals par ligue ──────────────────────────────────────────────

def test_expected_goals_uses_league_stats(poisson):
    """get_expected_goals utilise les stats de ligue quand disponibles."""
    # Stats PL : Arsenal forte attaque
    poisson.update_stats("Arsenal", 70, 20, 20, league_id=39)
    poisson.update_stats("Chelsea", 40, 40, 20, league_id=39)

    xg_pl_h, xg_pl_a = poisson.get_expected_goals("Arsenal", "Chelsea", league_id=39)

    # Stats UCL : Arsenal faible attaque
    poisson.update_stats("Arsenal", 5, 15, 5, league_id=2)
    poisson.update_stats("Chelsea", 5, 10, 5, league_id=2)

    xg_ucl_h, xg_ucl_a = poisson.get_expected_goals("Arsenal", "Chelsea", league_id=2)

    assert xg_pl_h > xg_ucl_h   # Arsenal marque plus en PL qu'en UCL


# ── predict_match par ligue ───────────────────────────────────────────────────

def test_predict_match_with_league_id(poisson):
    poisson.update_stats("Bayern",   80, 20, 20, league_id=78)
    poisson.update_stats("Dortmund", 60, 40, 20, league_id=78)

    result = poisson.predict_match("Bayern", "Dortmund", league_id=78)

    assert "home" in result and "draw" in result and "away" in result
    total = result["home"] + result["draw"] + result["away"]
    assert abs(total - 1.0) < 1e-5


def test_predict_match_favours_stronger_team(poisson):
    poisson.update_stats("Bayern",   80, 10, 20, league_id=78)  # forte attaque, bonne défense
    poisson.update_stats("Dortmund", 30, 50, 20, league_id=78)  # faible attaque, mauvaise défense

    result = poisson.predict_match("Bayern", "Dortmund", league_id=78)

    assert result["home"] > result["away"]
