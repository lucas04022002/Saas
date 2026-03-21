import sys
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import EloRating


@pytest.fixture
def elo(tmp_path):
    e = EloRating(home_advantage=100, initial_rating=1500)
    e.history_file = str(tmp_path / "elo_ha.json")
    e.ratings = {}
    e.matches_played = {}
    e.home_advantages = {}
    return e


# ── _get_home_advantage ───────────────────────────────────────────────────────

def test_unknown_team_returns_global_default(elo):
    assert elo._get_home_advantage("NewTeam") == 100


def test_stored_value_returned(elo):
    elo.home_advantages["PSG"] = 145.0
    assert elo._get_home_advantage("PSG") == 145.0


# ── Mise à jour du HA ─────────────────────────────────────────────────────────

def test_ha_increases_after_home_overperformance(elo):
    """Une équipe qui gagne régulièrement à domicile voit son HA augmenter."""
    for _ in range(20):
        elo.ratings["Home"] = 1500
        elo.ratings["Away"] = 1500
        elo.update_ratings("Home", "Away", 2, 0)   # victoire à domicile
    assert elo._get_home_advantage("Home") > 100


def test_ha_decreases_after_home_losses(elo):
    """Une équipe qui perd systématiquement à domicile voit son HA diminuer."""
    for _ in range(20):
        elo.ratings["Home"] = 1500
        elo.ratings["Away"] = 1500
        elo.update_ratings("Home", "Away", 0, 2)   # défaite à domicile
    assert elo._get_home_advantage("Home") < 100


def test_ha_not_updated_for_away_team(elo):
    """Le HA n'est mis à jour que pour l'équipe qui joue à domicile."""
    elo.update_ratings("Home", "Away", 2, 0)
    assert "Away" not in elo.home_advantages


def test_ha_clamped_to_min(elo):
    """HA ne descend jamais sous HA_MIN (0)."""
    elo.home_advantages["Home"] = 2.0   # proche du plancher
    elo.ratings["Home"] = 1500
    elo.ratings["Away"] = 1500
    for _ in range(50):
        elo.update_ratings("Home", "Away", 0, 3)
    assert elo._get_home_advantage("Home") >= EloRating.HA_MIN


def test_ha_clamped_to_max(elo):
    """HA ne dépasse jamais HA_MAX (300)."""
    elo.home_advantages["Home"] = 298.0  # proche du plafond
    elo.ratings["Home"] = 1500
    elo.ratings["Away"] = 1500
    for _ in range(50):
        elo.update_ratings("Home", "Away", 5, 0)
    assert elo._get_home_advantage("Home") <= EloRating.HA_MAX


# ── Persistance ───────────────────────────────────────────────────────────────

def test_ha_saved_and_loaded(elo):
    elo.home_advantages["PSG"] = 155.0
    elo.save_ratings()

    elo2 = EloRating()
    elo2.history_file = elo.history_file
    elo2.load_ratings()

    assert abs(elo2.home_advantages.get("PSG", 0) - 155.0) < 0.01


def test_load_old_format_sets_empty_ha(elo, tmp_path):
    """Fichier sans home_advantages → dict vide, pas d'erreur."""
    import json
    old_file = tmp_path / "old.json"
    old_file.write_text(json.dumps({"ratings": {"PSG": 1600}, "matches_played": {}}))
    elo.history_file = str(old_file)
    elo.load_ratings()
    assert elo.home_advantages == {}


# ── Effet sur predict_match ───────────────────────────────────────────────────

def test_high_ha_increases_home_win_prob(elo):
    """Un HA élevé doit augmenter la prob de victoire à domicile."""
    elo.ratings["Home"] = 1500
    elo.ratings["Away"] = 1500

    elo.home_advantages["Home"] = 50
    pred_low = elo.predict_match("Home", "Away")

    elo.home_advantages["Home"] = 200
    pred_high = elo.predict_match("Home", "Away")

    assert pred_high["home"] > pred_low["home"]
