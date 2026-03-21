import json
import sys
import unicodedata
from pathlib import Path

from app.core.config import settings
from app.providers.prediction.base import PredictionInput, PredictionResult


class LocalPythonPredictionProvider:
    LEAGUE_NAME_TO_ID = {
        "premier league": 39,
        "premier league (ang)": 39,
        "ligue 1": 61,
        "ligue 1 (fra)": 61,
        "la liga": 140,
        "la liga (esp)": 140,
        "bundesliga": 78,
        "bundesliga (all)": 78,
        "serie a": 135,
        "serie a (ita)": 135,
        "ligue des champions": 2,
        "uefa champions league": 2,
    }

    def __init__(self) -> None:
        self.model_root = self._resolve_model_root()
        if str(self.model_root) not in sys.path:
            sys.path.insert(0, str(self.model_root))

        from prediction_engine import AdvancedPredictor

        self._predictor = AdvancedPredictor()
        self._configure_model_files()
        self._load_team_stats_into_poisson()

    @classmethod
    def _normalize_league_name(cls, league: str) -> str:
        normalized = unicodedata.normalize("NFKD", league)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        return " ".join(ascii_only.lower().strip().split())

    @classmethod
    def _to_league_id(cls, league: str | int | None) -> int | None:
        if league is None:
            return None
        if isinstance(league, int):
            return league

        raw = str(league).strip()
        if raw.isdigit():
            return int(raw)

        normalized = cls._normalize_league_name(raw)
        return cls.LEAGUE_NAME_TO_ID.get(normalized)

    def _resolve_model_root(self) -> Path:
        candidates: list[Path] = []

        if settings.prediction_model_root:
            candidates.append(Path(settings.prediction_model_root).expanduser())

        # repo root when running from backend/app/providers/prediction
        candidates.append(Path(__file__).resolve().parents[4])
        candidates.append(Path.cwd())

        for candidate in candidates:
            candidate = candidate.resolve()
            if (candidate / "prediction_engine.py").exists():
                return candidate

        raise RuntimeError(
            "prediction_engine.py not found. Set PREDICTION_MODEL_ROOT to the directory containing the prediction files."
        )

    def _configure_model_files(self) -> None:
        model_path = self.model_root / "xgboost_model.pkl"
        elo_path = self.model_root / "elo_ratings.json"

        if hasattr(self._predictor, "xgboost") and model_path.exists():
            self._predictor.xgboost.model_file = str(model_path)
            self._predictor.xgboost.load_model()

        if hasattr(self._predictor, "elo"):
            self._predictor.elo.history_file = str(elo_path)
            self._predictor.elo.load_ratings()

    def _load_team_stats_into_poisson(self) -> None:
        stats_file = self.model_root / "team_stats.json"
        if not stats_file.exists():
            return

        try:
            all_stats = json.loads(stats_file.read_text(encoding="utf-8"))
        except Exception:
            return

        fill_only_leagues = {"Ligue des Champions", "UEFA Europa League", "UEFA Europa Conference League"}

        # Domestic leagues first
        for league_name, data in all_stats.items():
            if league_name in fill_only_leagues:
                continue
            league_id = self._to_league_id(league_name)
            for team_name, stats in (data.get("stats", {}) or {}).items():
                self._predictor.poisson.update_stats(
                    team_name,
                    stats.get("goals_for", 0),
                    stats.get("goals_against", 0),
                    stats.get("matches_played", 0),
                    league_id=league_id,
                )

        # UEFA leagues fill missing teams only
        for league_name in fill_only_leagues:
            league_id = self._to_league_id(league_name)
            league_stats = (all_stats.get(league_name, {}) or {}).get("stats", {}) or {}
            for team_name, stats in league_stats.items():
                self._predictor.poisson.update_stats(
                    team_name,
                    stats.get("goals_for", 0),
                    stats.get("goals_against", 0),
                    stats.get("matches_played", 0),
                    league_id=league_id,
                )

    def predict_match(self, payload: PredictionInput) -> PredictionResult:
        league_id = self._to_league_id(payload.league)
        raw = self._predictor.predict_match(payload.home_team, payload.away_team, league_id=league_id)
        probs = raw.get("probabilities", {})
        xg = raw.get("expected_goals", {})

        return PredictionResult(
            home_prob=float(probs.get("home", 0.33)),
            draw_prob=float(probs.get("draw", 0.33)),
            away_prob=float(probs.get("away", 0.34)),
            expected_home_goals=float(xg.get("home", 1.2)),
            expected_away_goals=float(xg.get("away", 1.1)),
        )

    def health(self) -> dict[str, str]:
        return {"status": "ok", "provider": "local_python", "model_root": str(self.model_root)}
