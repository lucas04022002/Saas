import sys
import pytest
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import XGBoostPredictor, days_since_last_match as _days_since


# ── _days_since ───────────────────────────────────────────────────────────────

def test_days_since_basic():
    assert _days_since("2025-03-01", "2025-03-08") == 7


def test_days_since_capped_at_14():
    assert _days_since("2025-01-01", "2025-03-01") == 14


def test_days_since_same_day_is_zero():
    assert _days_since("2025-03-01", "2025-03-01") == 0


def test_days_since_none_last_returns_none():
    assert _days_since(None, "2025-03-08") is None


def test_days_since_none_current_returns_none():
    assert _days_since("2025-03-01", None) is None


def test_days_since_never_negative():
    # Date passée en dernier → diff négatif clamped à 0
    assert _days_since("2025-03-08", "2025-03-01") == 0


# ── create_features avec fatigue ─────────────────────────────────────────────

@pytest.fixture
def xgb():
    return XGBoostPredictor()


def _base_args(xgb):
    return dict(
        home_team="Home", away_team="Away",
        elo_ratings={"Home": 1500, "Away": 1500},
        poisson_stats={
            "Home": {"attack": 1.5, "defense": 1.2},
            "Away": {"attack": 1.2, "defense": 1.3},
        },
    )


def test_feature_vector_size_without_rest(xgb):
    feat = xgb.create_features(**_base_args(xgb))
    assert feat.shape == (1, 57)


# Indices des features fatigue dans le vecteur de 57 features :
# 44 = home_days_rest, 45 = away_days_rest, 46 = rest_advantage
_H_REST = 44
_A_REST = 45
_R_ADV  = 46


def test_default_rest_is_neutral(xgb):
    """Sans info de repos, les features fatigue doivent être [7, 7, 0]."""
    feat = xgb.create_features(**_base_args(xgb))
    assert feat[0, _H_REST] == 7
    assert feat[0, _A_REST] == 7
    assert feat[0, _R_ADV]  == 0


def test_rest_advantage_positive_when_home_more_rested(xgb):
    feat = xgb.create_features(**_base_args(xgb), home_days_rest=10, away_days_rest=3)
    assert feat[0, _R_ADV] == 7   # 10 - 3


def test_rest_advantage_negative_when_away_more_rested(xgb):
    feat = xgb.create_features(**_base_args(xgb), home_days_rest=2, away_days_rest=9)
    assert feat[0, _R_ADV] == -7  # 2 - 9


def test_rest_capped_at_14(xgb):
    feat = xgb.create_features(**_base_args(xgb), home_days_rest=100, away_days_rest=0)
    assert feat[0, _H_REST] == 14
    assert feat[0, _A_REST] == 0
    assert feat[0, _R_ADV]  == 14


def test_none_rest_uses_default_7(xgb):
    feat_none = xgb.create_features(**_base_args(xgb), home_days_rest=None, away_days_rest=None)
    feat_7    = xgb.create_features(**_base_args(xgb), home_days_rest=7,    away_days_rest=7)
    np.testing.assert_array_equal(feat_none, feat_7)
