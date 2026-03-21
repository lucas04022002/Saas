import sys
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import EloRating


@pytest.fixture
def elo(tmp_path):
    e = EloRating(home_advantage=100, initial_rating=1500)
    e.history_file = str(tmp_path / "elo_mov.json")
    e.ratings = {}
    e.matches_played = {}
    return e


# ── Multiplicateur MOV ───────────────────────────────────────────────────────

def test_mov_draw_is_1():
    assert EloRating._mov_multiplier(1, 1) == 1.0
    assert EloRating._mov_multiplier(0, 0) == 1.0


def test_mov_diff1_is_1():
    assert EloRating._mov_multiplier(1, 0) == 1.0
    assert EloRating._mov_multiplier(0, 1) == 1.0


def test_mov_diff2_is_1_5():
    assert EloRating._mov_multiplier(2, 0) == 1.5
    assert EloRating._mov_multiplier(0, 2) == 1.5


def test_mov_diff3_formula():
    # (11 + 3) / 8 = 1.75
    assert abs(EloRating._mov_multiplier(3, 0) - 1.75) < 1e-9


def test_mov_diff5_formula():
    # (11 + 5) / 8 = 2.0
    assert abs(EloRating._mov_multiplier(5, 0) - 2.0) < 1e-9


def test_mov_increases_with_diff():
    m1 = EloRating._mov_multiplier(1, 0)
    m2 = EloRating._mov_multiplier(2, 0)
    m3 = EloRating._mov_multiplier(3, 0)
    m4 = EloRating._mov_multiplier(4, 0)
    assert m1 <= m2 <= m3 <= m4


# ── Effet sur update_ratings ─────────────────────────────────────────────────

def test_big_win_gives_more_points_than_narrow_win(elo):
    """Gagner 4-0 doit rapporter plus de points Elo que gagner 1-0."""
    # Match 1 : victoire 1-0
    elo.ratings["HomeA"] = 1500
    elo.ratings["AwayA"] = 1500
    elo.matches_played = {"HomeA": 30, "AwayA": 30}
    before = elo.get_rating("HomeA")
    elo.update_ratings("HomeA", "AwayA", 1, 0)
    delta_narrow = elo.get_rating("HomeA") - before

    # Match 2 : victoire 4-0 (même ratings de départ)
    elo.ratings["HomeB"] = 1500
    elo.ratings["AwayB"] = 1500
    elo.matches_played["HomeB"] = 30
    elo.matches_played["AwayB"] = 30
    before = elo.get_rating("HomeB")
    elo.update_ratings("HomeB", "AwayB", 4, 0)
    delta_big = elo.get_rating("HomeB") - before

    assert delta_big > delta_narrow


def test_loser_loses_more_on_big_defeat(elo):
    """Perdre 0-4 doit coûter plus de points que perdre 0-1."""
    elo.ratings["Away1"] = 1500
    elo.ratings["Home1"] = 1500
    elo.matches_played = {"Away1": 30, "Home1": 30, "Away2": 30, "Home2": 30}
    before1 = elo.get_rating("Away1")
    elo.update_ratings("Home1", "Away1", 1, 0)
    delta_narrow = elo.get_rating("Away1") - before1

    elo.ratings["Away2"] = 1500
    elo.ratings["Home2"] = 1500
    before2 = elo.get_rating("Away2")
    elo.update_ratings("Home2", "Away2", 4, 0)
    delta_big = elo.get_rating("Away2") - before2

    assert delta_big < delta_narrow  # les deux sont négatifs, big est plus négatif


def test_draw_unaffected_by_mov(elo):
    """Pour un nul (diff=0), MOV=1 donc comportement identique à avant."""
    elo.ratings["H"] = 1600
    elo.ratings["A"] = 1500
    elo.matches_played = {"H": 30, "A": 30}
    before_h = elo.get_rating("H")
    elo.update_ratings("H", "A", 1, 1)
    # Le favori (H) doit perdre des points après un nul
    assert elo.get_rating("H") < before_h
