"""Probabilités implicites et marge. Aucune prédiction ici : on lit le marché."""
from app.engine.types import Odds, Probs

REFERENCE_BOOKMAKER = "pinnacle"


def implied(odds: Odds) -> Probs:
    inv = tuple(1.0 / o for o in odds)
    s = sum(inv)
    return (inv[0] / s, inv[1] / s, inv[2] / s)


def margin(odds: Odds) -> float:
    return sum(1.0 / o for o in odds) - 1.0


def reference(latest: dict[str, Odds]) -> tuple[Probs, str]:
    """Pinnacle si présent, sinon la moyenne des probabilités implicites des bookmakers disponibles."""
    if not latest:
        raise ValueError("aucune cote disponible")
    if REFERENCE_BOOKMAKER in latest:
        return implied(latest[REFERENCE_BOOKMAKER]), "pinnacle"
    ps = [implied(o) for o in latest.values()]
    n = len(ps)
    mean = (sum(p[0] for p in ps) / n, sum(p[1] for p in ps) / n, sum(p[2] for p in ps) / n)
    s = sum(mean)
    return (mean[0] / s, mean[1] / s, mean[2] / s), "moyenne"
