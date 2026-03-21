import sys
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import kelly_fraction


# ── Formule de base ───────────────────────────────────────────────────────────

def test_no_edge_returns_zero():
    """Proba implicite == proba modèle → pas d'edge → 0."""
    # cote 2.0 → proba implicite 50% ; si modèle dit aussi 50% → f=0
    assert kelly_fraction(0.50, 2.0) == 0.0


def test_negative_edge_returns_zero():
    """Modèle moins optimiste que les bookmakers → pas de mise."""
    assert kelly_fraction(0.40, 2.0) == 0.0


def test_positive_edge_returns_positive():
    """Modèle plus optimiste → fraction positive."""
    assert kelly_fraction(0.60, 2.0) > 0.0


def test_half_kelly_applied():
    """fraction=0.5 → résultat = Kelly complet / 2."""
    # Kelly complet pour p=0.6, cote=2.0 : b=1, f=(0.6-0.4)/1=0.2
    full = kelly_fraction(0.60, 2.0, fraction=1.0)
    half = kelly_fraction(0.60, 2.0, fraction=0.5)
    assert abs(half - full / 2) < 1e-9


def test_full_kelly_formula():
    """Vérifie la formule exacte : f = (p*b - q) / b."""
    p, odd = 0.65, 1.80
    b = odd - 1  # 0.80
    q = 1 - p   # 0.35
    expected = (p * b - q) / b  # Kelly complet
    result = kelly_fraction(p, odd, fraction=1.0, max_bet=1.0)
    assert abs(result - expected) < 1e-9


def test_max_bet_cap():
    """Mise plafonnée à max_bet même si Kelly est très élevé."""
    # p=0.95, cote=5.0 → Kelly très élevé
    result = kelly_fraction(0.95, 5.0, fraction=1.0, max_bet=0.25)
    assert result == 0.25


def test_invalid_odd_returns_zero():
    assert kelly_fraction(0.60, 1.0) == 0.0   # odd <= 1
    assert kelly_fraction(0.60, 0.5) == 0.0


def test_invalid_prob_returns_zero():
    assert kelly_fraction(0.0, 2.0) == 0.0
    assert kelly_fraction(1.0, 2.0) == 0.0
    assert kelly_fraction(-0.1, 2.0) == 0.0


def test_typical_value_bet():
    """Scénario réaliste : modèle 62%, cote 1.90 (bookmaker donne 53.7%)."""
    result = kelly_fraction(0.62, 1.90, fraction=0.5)
    # Kelly complet : b=0.9, f=(0.62*0.9 - 0.38)/0.9 = (0.558-0.38)/0.9 ≈ 0.198
    # Demi-Kelly ≈ 0.099 → ~10% du bankroll
    assert 0.08 < result < 0.15
