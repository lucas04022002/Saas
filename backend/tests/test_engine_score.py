import pytest

from app.engine import score as score_mod
from app.engine.probabilities import implied
from app.engine.score import DEFAULT_GOALS, LEAGUE_GOALS, most_probable_score


def test_full_grid_sums_to_one():
    m = score_mod._matrix(1.5, 1.2)
    assert sum(sum(row) for row in m) == pytest.approx(1.0, abs=1e-3)


def test_home_favourite_top_is_home_win_and_matches_implied_difference():
    p_home, p_draw, p_away = implied((1.50, 4.20, 6.50))
    d = most_probable_score(p_home, p_draw, p_away, DEFAULT_GOALS, "home")
    i, j = (int(x) for x in d.top.split("-"))
    assert i > j
    m = score_mod._matrix(d.lambda_home, d.lambda_away)
    h, _, a = score_mod._outcome_probs(m)
    assert (h - a) == pytest.approx(p_home - p_away, abs=0.01)


def test_away_favourite_top_is_away_win():
    p_home, p_draw, p_away = implied((2.90, 3.10, 2.60))
    d = most_probable_score(p_home, p_draw, p_away, DEFAULT_GOALS, "away")
    i, j = (int(x) for x in d.top.split("-"))
    assert i < j


def test_draw_favourite_top_is_a_draw_score():
    p_home, p_draw, p_away = implied((3.40, 3.10, 3.50))
    d = most_probable_score(p_home, p_draw, p_away, DEFAULT_GOALS, "draw")
    i, j = (int(x) for x in d.top.split("-"))
    assert i == j


def test_higher_total_goals_yields_a_higher_scoring_top():
    p_home, p_draw, p_away = implied((1.90, 3.60, 4.20))
    low = most_probable_score(p_home, p_draw, p_away, LEAGUE_GOALS["I1"], "home")
    high = most_probable_score(p_home, p_draw, p_away, LEAGUE_GOALS["D1"], "home")
    assert low.top != high.top
    sum_goals = lambda s: sum(int(x) for x in s.split("-"))
    assert sum_goals(high.top) > sum_goals(low.top)


def test_none_when_any_probability_missing():
    assert most_probable_score(None, 0.3, 0.3, DEFAULT_GOALS, "home") is None
    assert most_probable_score(0.4, None, 0.3, DEFAULT_GOALS, "home") is None
    assert most_probable_score(0.4, 0.3, None, DEFAULT_GOALS, "home") is None


# --- Golden : 3 matchs réels 2025/26 (dev.db, cotes de clôture Pinnacle/moyenne, variante D) ---
# Rejoués avec backend/scripts/mesure_scores_v2.py le 11/09/2026 ; total de buts = LEAGUE_GOALS de la ligue.

GOLDEN = [
    # (compétition, cotes h/n/a, score attendu, proba attendue à 1e-3 près)
    ("SP1", (2.25, 3.17, 3.73), "1-0", 0.104),
    ("F1", (1.59, 4.22, 5.14), "1-0", 0.112),
    ("I1", (2.03, 3.20, 4.47), "1-0", 0.131),
]


@pytest.mark.parametrize("competition,odds,expected_top,expected_prob", GOLDEN)
def test_golden_real_2025_26_matches(competition, odds, expected_top, expected_prob):
    p_home, p_draw, p_away = implied(odds)
    fav = max(("home", p_home), ("draw", p_draw), ("away", p_away), key=lambda t: t[1])[0]
    d = most_probable_score(p_home, p_draw, p_away, LEAGUE_GOALS[competition], fav)
    assert d.top == expected_top
    assert d.top_probability == pytest.approx(expected_prob, abs=1e-3)
