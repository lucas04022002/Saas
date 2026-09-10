from dataclasses import dataclass, field
from datetime import datetime

Odds = tuple[float, float, float]     # domicile, nul, extérieur — cotes décimales
Probs = tuple[float, float, float]    # domicile, nul, extérieur — somme = 1
OUTCOMES = ("home", "draw", "away")


@dataclass(frozen=True)
class BookQuote:
    bookmaker: str
    taken_at: datetime
    odds: Odds


@dataclass
class Reading:
    reference: Probs
    reference_source: str                          # "pinnacle" | "moyenne"
    favourite: str                                 # "home" | "draw" | "away"
    favourite_prob: float
    margin_by_book: dict[str, float] = field(default_factory=dict)          # bookmaker -> marge (0.06 = 6 %)
    latest_by_book: dict[str, Odds] = field(default_factory=dict)          # bookmaker -> dernières cotes
    gaps: dict[str, tuple[float, float, float]] = field(default_factory=dict)   # bookmaker -> écart par issue (0.03 = +3 %)
    movement: tuple[float, float, float] | None = None                     # points de % de la référence, premier → dernier relevé
    first_taken_at: datetime | None = None
    last_taken_at: datetime | None = None
