import math

import pytest

from app.engine import score as score_mod
from app.engine.probabilities import implied
from app.engine.score import DEFAULT_GOALS, LEAGUE_GOALS, expected_total, most_probable_score, total_goals_from_market


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


# --- total de buts déduit du marché over/under (complément du 11/09/2026 à la mesure) ---

def test_total_goals_from_market_matches_implied_over_probability():
    over, under, line = 1.85, 2.05, 2.5
    lam = total_goals_from_market(over, under, line)
    assert 2.7 <= lam <= 2.9
    p_over_implied = (1 / over) / (1 / over + 1 / under)
    p_over_recomputed = 1 - sum(score_mod._pois(lam, i) for i in range(math.floor(line) + 1))
    assert p_over_recomputed == pytest.approx(p_over_implied, abs=0.005)


def test_total_goals_from_market_none_for_non_half_line():
    assert total_goals_from_market(1.85, 2.05, 2.75) is None
    assert total_goals_from_market(1.85, 2.05, 2.25) is None
    assert total_goals_from_market(1.85, 2.05, 2.0) is None


def test_total_goals_from_market_none_when_odds_missing_or_invalid():
    assert total_goals_from_market(None, 2.05, 2.5) is None
    assert total_goals_from_market(1.85, None, 2.5) is None
    assert total_goals_from_market(1.85, 2.05, None) is None
    assert total_goals_from_market(0.9, 2.05, 2.5) is None


class _FakeTotalsSnapshot:
    def __init__(self, over, under, line):
        self.over, self.under, self.line = over, under, line


def test_expected_total_uses_market_when_line_is_usable():
    total, source = expected_total("I1", _FakeTotalsSnapshot(1.85, 2.05, 2.5))
    assert source == "marché"
    assert 2.7 <= total <= 2.9


def test_expected_total_falls_back_to_league_without_snapshot():
    assert expected_total("I1", None) == (LEAGUE_GOALS["I1"], "ligue")


def test_expected_total_falls_back_to_league_when_line_unusable():
    assert expected_total("I1", _FakeTotalsSnapshot(1.85, 2.05, 2.75)) == (LEAGUE_GOALS["I1"], "ligue")


def test_expected_total_falls_back_to_default_for_unknown_competition():
    assert expected_total("XX", None) == (DEFAULT_GOALS, "ligue")
