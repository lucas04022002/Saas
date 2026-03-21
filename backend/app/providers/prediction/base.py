from dataclasses import dataclass
from typing import Protocol


@dataclass
class PredictionInput:
    home_team: str
    away_team: str
    league: str | None = None


@dataclass
class PredictionResult:
    home_prob: float
    draw_prob: float
    away_prob: float
    expected_home_goals: float
    expected_away_goals: float


class PredictionProvider(Protocol):
    def predict_match(self, payload: PredictionInput) -> PredictionResult:
        ...

    def health(self) -> dict[str, str]:
        ...
