import json
import threading
from pathlib import Path

from app.core.config import settings
from app.models.enums import RiskLevel
from app.providers.prediction.base import PredictionInput, PredictionProvider
from app.providers.prediction.local_python_provider import LocalPythonPredictionProvider
from app.providers.prediction.mock_provider import MockPredictionProvider


class PredictionService:
    DRAW_PROB_MIN = 0.25
    DRAW_BALANCE_MAX = 0.10
    DRAW_MARGIN_TO_BEST = 0.05
    _DRAW_CFG_CACHE: dict | None = None
    _DRAW_CFG_LOCK: threading.Lock = threading.Lock()

    def __init__(self, provider: PredictionProvider, provider_name: str, warning: str | None = None) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.warning = warning

    @classmethod
    def _to_ratio(cls, value: float) -> float:
        v = float(value)
        return v / 100.0 if v > 1.0 else v

    @classmethod
    def _load_draw_cfg(cls) -> dict:
        if cls._DRAW_CFG_CACHE is not None:
            return cls._DRAW_CFG_CACHE

        with cls._DRAW_CFG_LOCK:
            # Double-checked locking: another thread may have populated the cache
            if cls._DRAW_CFG_CACHE is not None:
                return cls._DRAW_CFG_CACHE

            root = Path(__file__).resolve().parents[3]
            cfg_path = root / "draw_thresholds_by_league.json"
            if not cfg_path.exists():
                cls._DRAW_CFG_CACHE = {}
                return cls._DRAW_CFG_CACHE

            try:
                with cfg_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                cls._DRAW_CFG_CACHE = data if isinstance(data, dict) else {}
            except Exception:
                cls._DRAW_CFG_CACHE = {}
        return cls._DRAW_CFG_CACHE

    @classmethod
    def _thresholds_for_league(cls, league: str | None) -> dict[str, float]:
        cfg = cls._load_draw_cfg()
        default_cfg = cfg.get("default", {}) if isinstance(cfg, dict) else {}
        leagues_cfg = cfg.get("leagues", {}) if isinstance(cfg, dict) else {}

        selected_cfg = {}
        if league:
            selected_cfg = leagues_cfg.get(league, {})
            if not selected_cfg:
                normalized = league.strip().lower()
                for key, value in leagues_cfg.items():
                    if isinstance(key, str) and key.strip().lower() == normalized:
                        selected_cfg = value
                        break
        if not isinstance(selected_cfg, dict):
            selected_cfg = {}

        draw_prob_min = cls._to_ratio(selected_cfg.get("draw_prob_min", default_cfg.get("draw_prob_min", cls.DRAW_PROB_MIN)))
        draw_balance_max = cls._to_ratio(selected_cfg.get("draw_balance_max", default_cfg.get("draw_balance_max", cls.DRAW_BALANCE_MAX)))
        draw_margin_to_best = cls._to_ratio(selected_cfg.get("draw_margin_to_best", default_cfg.get("draw_margin_to_best", cls.DRAW_MARGIN_TO_BEST)))

        return {
            "draw_prob_min": draw_prob_min,
            "draw_balance_max": draw_balance_max,
            "draw_margin_to_best": draw_margin_to_best,
        }

    @classmethod
    def _select_recommended_outcome(cls, probs: dict[str, float], league: str | None = None) -> str:
        home = float(probs.get("home", 0.0))
        draw = float(probs.get("draw", 0.0))
        away = float(probs.get("away", 0.0))
        thresholds = cls._thresholds_for_league(league)

        best_non_draw = max(home, away)
        # On autorise le nul quand la proba est solide et que le match est équilibré.
        if (
            draw >= thresholds["draw_prob_min"]
            and abs(home - away) <= thresholds["draw_balance_max"]
            and draw >= best_non_draw - thresholds["draw_margin_to_best"]
        ):
            return "draw"

        return "home" if home >= away else "away"

    def get_prediction(
        self,
        home_team: str,
        away_team: str,
        league: str | None = None,
        odds_by_outcome: dict[str, float] | None = None,
    ) -> dict:
        prediction = self.provider.predict_match(PredictionInput(home_team=home_team, away_team=away_team, league=league))

        probs = {
            "home": prediction.home_prob,
            "draw": prediction.draw_prob,
            "away": prediction.away_prob,
        }
        recommended_bet = self._select_recommended_outcome(probs, league=league)
        confidence_score = round(probs[recommended_bet] * 100, 2)

        bookmaker_odds = odds_by_outcome.get(recommended_bet, 1.95) if odds_by_outcome else 1.95

        implied = (1 / bookmaker_odds) * 100
        value_percent = round(confidence_score - implied, 2)

        if confidence_score >= 62:
            risk = RiskLevel.LOW
        elif confidence_score >= 52:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.HIGH

        short_label = {"home": "Victoire domicile", "draw": "Match nul", "away": "Victoire exterieur"}

        return {
            "probabilities": probs,
            "confidence_score": confidence_score,
            "recommended_bet": short_label[recommended_bet],
            "bookmaker_odds": bookmaker_odds,
            "value_percent": value_percent,
            "risk_level": risk.value,
            "expected_home_goals": prediction.expected_home_goals,
            "expected_away_goals": prediction.expected_away_goals,
            "ai_explanation": (
                f"Le modele donne {confidence_score}% sur '{short_label[recommended_bet]}'. "
                f"xG attendus: {prediction.expected_home_goals:.2f}-{prediction.expected_away_goals:.2f}."
            ),
        }

    def health(self) -> dict[str, str]:
        base = self.provider.health()
        base["active_provider"] = self.provider_name
        if self.warning:
            base["warning"] = self.warning
        return base


def build_prediction_service() -> PredictionService:
    if settings.prediction_provider == "mock":
        provider: PredictionProvider = MockPredictionProvider()
        return PredictionService(provider=provider, provider_name="mock")

    try:
        provider = LocalPythonPredictionProvider()
        return PredictionService(provider=provider, provider_name="local_python")
    except Exception as exc:
        fallback = MockPredictionProvider()
        warning = f"Local provider unavailable, fallback to mock: {exc}"
        return PredictionService(provider=fallback, provider_name="mock_fallback", warning=warning)


prediction_service = build_prediction_service()
