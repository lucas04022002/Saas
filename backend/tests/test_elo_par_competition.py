import sys
import json
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import EloRating


@pytest.fixture
def elo(tmp_path):
    e = EloRating(home_advantage=100, initial_rating=1500)
    e.history_file = str(tmp_path / "elo_comp.json")
    e.ratings = {}
    e.matches_played = {}
    e.home_advantages = {}
    return e


# ── _key helper ──────────────────────────────────────────────────────────────

def test_key_without_league_returns_team_name(elo):
    assert elo._key("PSG") == "PSG"


def test_key_with_league_returns_prefixed(elo):
    assert elo._key("PSG", league_id=61) == "61:PSG"


# ── Ratings indépendants par ligue ───────────────────────────────────────────

def test_win_in_one_league_does_not_affect_other(elo):
    """PSG gagne en Ligue 1 → son rating UCL reste initial."""
    elo.update_ratings("PSG", "OM", 3, 0, league_id=61)

    rating_l1  = elo.get_rating("PSG", league_id=61)
    rating_ucl = elo.get_rating("PSG", league_id=2)

    assert rating_l1 > 1500   # gagné en L1
    assert rating_ucl == 1500  # jamais joué en UCL → rating initial


def test_loss_in_one_league_does_not_affect_other(elo):
    """PSG perd en UCL → son rating L1 reste initial."""
    elo.update_ratings("PSG", "Real", 0, 3, league_id=2)

    assert elo.get_rating("PSG", league_id=2) < 1500
    assert elo.get_rating("PSG", league_id=61) == 1500


def test_two_leagues_independently_tracked(elo):
    """Bayern gagne fort en Bundesliga et perd en UCL : ratings différents."""
    elo.update_ratings("Bayern", "BVB",  5, 0, league_id=78)
    elo.update_ratings("Bayern", "Real", 0, 3, league_id=2)

    assert elo.get_rating("Bayern", league_id=78) > 1500
    assert elo.get_rating("Bayern", league_id=2) < 1500


# ── Fallback migration (ancien format sans league) ───────────────────────────

def test_fallback_to_plain_rating_when_no_league_specific(elo):
    """Si pas de rating ligue, on utilise le rating sans league (ancien format)."""
    elo.ratings["Arsenal"] = 1650
    assert elo.get_rating("Arsenal", league_id=39) == 1650


def test_league_specific_rating_takes_priority_over_fallback(elo):
    """Le rating ligue-spécifique est prioritaire sur le rating sans league."""
    elo.ratings["Arsenal"] = 1650
    elo.ratings["39:Arsenal"] = 1720
    assert elo.get_rating("Arsenal", league_id=39) == 1720


def test_no_league_key_returns_plain_rating(elo):
    """Sans league_id, get_rating renvoie le rating sans préfixe."""
    elo.ratings["Arsenal"] = 1650
    assert elo.get_rating("Arsenal") == 1650


# ── Compteurs matches_played par ligue ───────────────────────────────────────

def test_matches_played_keyed_per_league(elo):
    elo.update_ratings("Team", "Other",  1, 0, league_id=39)
    elo.update_ratings("Team", "Other2", 1, 0, league_id=61)

    assert elo.matches_played.get("39:Team", 0) == 1
    assert elo.matches_played.get("61:Team", 0) == 1
    # Clé sans league doit être absente (car league_id était fourni)
    assert elo.matches_played.get("Team", 0) == 0


# ── Home advantage par ligue ─────────────────────────────────────────────────

def test_ha_learned_per_league(elo):
    """HA appris en PL ne contamine pas le HA UCL."""
    for _ in range(15):
        elo.ratings["39:HomeTeam"] = 1500
        elo.ratings["39:Visitor"] = 1500
        elo.update_ratings("HomeTeam", "Visitor", 2, 0, league_id=39)

    ha_pl  = elo.home_advantages.get("39:HomeTeam", elo.home_advantage)
    ha_ucl = elo.home_advantages.get("2:HomeTeam",  elo.home_advantage)

    assert ha_pl > elo.home_advantage    # HA monte en PL après 15 victoires
    assert ha_ucl == elo.home_advantage  # HA UCL inchangé (jamais joué là)


# ── Persistance ──────────────────────────────────────────────────────────────

def test_persist_and_reload_league_ratings(elo):
    """Les ratings par ligue sont sauvegardés et rechargés correctement."""
    elo.update_ratings("PSG", "OM", 3, 0, league_id=61)
    rating_before = elo.get_rating("PSG", league_id=61)
    elo.save_ratings()

    elo2 = EloRating()
    elo2.history_file = elo.history_file
    elo2.load_ratings()

    assert abs(elo2.get_rating("PSG", league_id=61) - rating_before) < 0.01


def test_persist_and_reload_matches_played_per_league(elo):
    elo.update_ratings("PSG", "OM", 1, 1, league_id=61)
    elo.save_ratings()

    elo2 = EloRating()
    elo2.history_file = elo.history_file
    elo2.load_ratings()

    assert elo2.matches_played.get("61:PSG") == 1


# ── predict_match par ligue ───────────────────────────────────────────────────

def test_predict_uses_league_specific_rating(elo):
    """predict_match retourne les bons ratings par ligue."""
    elo.ratings["39:Man City"] = 1750
    elo.ratings["39:Liverpool"] = 1680

    result = elo.predict_match("Man City", "Liverpool", league_id=39)

    assert result["home_rating"] == 1750
    assert result["away_rating"] == 1680


def test_predict_without_league_uses_plain_key(elo):
    """predict_match sans league_id utilise les clés sans préfixe."""
    elo.ratings["PSG"] = 1700
    elo.ratings["OM"]  = 1550

    result = elo.predict_match("PSG", "OM")

    assert result["home_rating"] == 1700
    assert result["away_rating"] == 1550
