from app.providers.prediction.base import PredictionInput, PredictionResult


class MockPredictionProvider:
    def predict_match(self, payload: PredictionInput) -> PredictionResult:
        return PredictionResult(
            home_prob=0.47,
            draw_prob=0.26,
            away_prob=0.27,
            expected_home_goals=1.62,
            expected_away_goals=1.18,
        )

    def health(self) -> dict[str, str]:
        return {"status": "ok", "provider": "mock"}
