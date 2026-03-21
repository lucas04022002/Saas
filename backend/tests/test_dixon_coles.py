import sys
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import PoissonPredictor


@pytest.fixture
def poisson():
    p = PoissonPredictor(rho=-0.13)
    p.team_stats = {
        "Home": {"attack": 1.6, "defense": 1.1},
        "Away": {"attack": 1.1, "defense": 1.3},
    }
    return p


# ── Facteur τ ────────────────────────────────────────────────────────────────

def test_tau_00_greater_than_1(poisson):
    """ρ < 0 ⟹ τ(0,0) = 1 - λμρ > 1 (booste les 0-0)"""
    tau = poisson._dixon_coles_tau(0, 0, 1.5, 1.2, -0.13)
    assert tau > 1.0


def test_tau_11_greater_than_1(poisson):
    """ρ < 0 ⟹ τ(1,1) = 1 - ρ > 1 (booste les 1-1)"""
    tau = poisson._dixon_coles_tau(1, 1, 1.5, 1.2, -0.13)
    assert tau > 1.0


def test_tau_10_less_than_1(poisson):
    """ρ < 0 ⟹ τ(1,0) = 1 + μρ < 1 (réduit les 1-0)"""
    tau = poisson._dixon_coles_tau(1, 0, 1.5, 1.2, -0.13)
    assert tau < 1.0


def test_tau_01_less_than_1(poisson):
    """ρ < 0 ⟹ τ(0,1) = 1 + λρ < 1 (réduit les 0-1)"""
    tau = poisson._dixon_coles_tau(0, 1, 1.5, 1.2, -0.13)
    assert tau < 1.0


def test_tau_high_scores_is_1(poisson):
    """Pour x+y > 1, τ = 1 (pas de correction)"""
    for x, y in [(2, 0), (0, 2), (3, 1), (2, 2)]:
        assert poisson._dixon_coles_tau(x, y, 1.5, 1.2, -0.13) == 1.0


def test_tau_00_formula(poisson):
    lam, mu, rho = 1.5, 1.2, -0.13
    expected = 1.0 - lam * mu * rho
    assert abs(poisson._dixon_coles_tau(0, 0, lam, mu, rho) - expected) < 1e-10


# ── Effet sur les probabilités ───────────────────────────────────────────────

def test_dc_increases_draw_prob_vs_plain_poisson(poisson):
    """La correction Dixon-Coles doit augmenter la proba de match nul."""
    dc_pred = poisson.predict_match("Home", "Away")

    plain = PoissonPredictor(rho=0.0)
    plain.team_stats = poisson.team_stats
    plain_pred = plain.predict_match("Home", "Away")

    assert dc_pred["draw"] > plain_pred["draw"]


def test_probabilities_sum_to_one(poisson):
    pred = poisson.predict_match("Home", "Away")
    total = pred["home"] + pred["draw"] + pred["away"]
    assert abs(total - 1.0) < 1e-6


def test_home_team_still_favoured(poisson):
    """L'équipe à domicile (meilleure attaque) reste favorite."""
    pred = poisson.predict_match("Home", "Away")
    assert pred["home"] > pred["away"]
