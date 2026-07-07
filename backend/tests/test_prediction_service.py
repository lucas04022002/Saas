import pytest

from app.providers.prediction.base import PredictionInput, PredictionResult
from app.services.prediction_service import PredictionService


class DrawHeavyProvider:
    def predict_match(self, payload: PredictionInput) -> PredictionResult:
        return PredictionResult(
            home_prob=0.29,
            draw_prob=0.41,
            away_prob=0.30,
            expected_home_goals=1.10,
            expected_away_goals=1.05,
        )

    def health(self) -> dict[str, str]:
        return {"status": "ok"}


class NearDrawProvider:
    def predict_match(self, payload: PredictionInput) -> PredictionResult:
        return PredictionResult(
            home_prob=0.35,
            draw_prob=0.33,
            away_prob=0.32,
            expected_home_goals=1.15,
            expected_away_goals=1.10,
        )

    def health(self) -> dict[str, str]:
        return {"status": "ok"}


class UnbalancedProvider:
    def predict_match(self, payload: PredictionInput) -> PredictionResult:
        return PredictionResult(
            home_prob=0.52,
            draw_prob=0.31,
            away_prob=0.17,
            expected_home_goals=1.70,
            expected_away_goals=0.80,
        )

    def health(self) -> dict[str, str]:
        return {"status": "ok"}


def test_prediction_returns_expected_keys(prediction_svc):
    result = prediction_svc.get_prediction("Arsenal", "Chelsea", "Premier League")
    assert {"probabilities", "confidence_score", "recommended_bet",
            "bookmaker_odds", "value_percent", "risk_level",
            "expected_home_goals", "expected_away_goals", "ai_explanation"} == set(result.keys())


def test_recommended_bet_is_draw_when_draw_highest():
    svc = PredictionService(provider=DrawHeavyProvider(), provider_name="draw-heavy")
    result = svc.get_prediction("Team A", "Team B")
    assert result["recommended_bet"] == "Match nul"


def test_recommended_bet_is_draw_when_close_and_balanced():
    svc = PredictionService(provider=NearDrawProvider(), provider_name="near-draw")
    result = svc.get_prediction("Team A", "Team B")
    assert result["recommended_bet"] == "Match nul"


def test_recommended_bet_stays_home_when_match_unbalanced():
    svc = PredictionService(provider=UnbalancedProvider(), provider_name="unbalanced")
    result = svc.get_prediction("Team A", "Team B")
    assert result["recommended_bet"] == "Victoire domicile"


def test_recommended_bet_is_home_when_home_highest(prediction_svc):
    """Mock retourne home=0.47 > away=0.27 → doit recommander Victoire domicile."""
    result = prediction_svc.get_prediction("Team A", "Team B")
    assert result["recommended_bet"] == "Victoire domicile"


def test_confidence_score_is_percentage(prediction_svc):
    result = prediction_svc.get_prediction("Team A", "Team B")
    assert 0 < result["confidence_score"] <= 100


def test_probabilities_sum_to_one(prediction_svc):
    result = prediction_svc.get_prediction("Team A", "Team B")
    total = sum(result["probabilities"].values())
    assert abs(total - 1.0) < 0.01


def test_risk_level_valid_values(prediction_svc):
    result = prediction_svc.get_prediction("Team A", "Team B")
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")


def test_custom_bookmaker_odds(prediction_svc):
    # L'API prend un dict par issue ; on fixe la même cote partout pour que
    # l'issue recommandée l'utilise quelle qu'elle soit.
    result = prediction_svc.get_prediction(
        "Team A", "Team B", odds_by_outcome={"home": 2.10, "draw": 2.10, "away": 2.10}
    )
    assert result["bookmaker_odds"] == 2.10
    implied = round((1 / 2.10) * 100, 2)
    assert result["value_percent"] == round(result["confidence_score"] - implied, 2)


def test_health_returns_provider_name(prediction_svc):
    h = prediction_svc.health()
    assert h["active_provider"] == "mock"


def test_no_warning_when_healthy(prediction_svc):
    h = prediction_svc.health()
    assert "warning" not in h
