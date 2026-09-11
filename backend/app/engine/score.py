"""Score le plus probable déduit du marché : Poisson calibré sur le 1N2, total de buts fixé par ligue.

Méthode et choix de la variante D (total de buts fixé, score cohérent avec le favori) mesurés dans
docs/mesures/2026-09-11-score-le-plus-probable.md — ne pas changer sans nouvelle mesure. Aucune prédiction :
c'est une traduction fidèle du marché en score, comme le reste du moteur.
"""
import math

from app.engine.types import ScoreDistribution, ScoreProbability

MAXG = 8

# Buts moyens mesurés sur la saison 2025/26 (football-data.co.uk, cotes de clôture) — sert de repli tant que le
# marché over/under n'est pas collecté. CL/EL et toute compétition inconnue utilisent DEFAULT_GOALS.
LEAGUE_GOALS = {"E0": 2.75, "F1": 2.82, "SP1": 2.69, "D1": 3.24, "I1": 2.43}
DEFAULT_GOALS = 2.75

_FAVOURITE_SIGN = {"home": 1, "draw": 0, "away": -1}


def _pois(lam: float, k: int) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def _matrix(lh: float, la: float) -> list[list[float]]:
    ph = [_pois(lh, k) for k in range(MAXG + 1)]
    pa = [_pois(la, k) for k in range(MAXG + 1)]
    return [[ph[i] * pa[j] for j in range(MAXG + 1)] for i in range(MAXG + 1)]


def _outcome_probs(m: list[list[float]]) -> tuple[float, float, float]:
    h = sum(m[i][j] for i in range(MAXG + 1) for j in range(MAXG + 1) if i > j)
    d = sum(m[i][i] for i in range(MAXG + 1))
    a = sum(m[i][j] for i in range(MAXG + 1) for j in range(MAXG + 1) if i < j)
    return h, d, a


def _fit_sum(p_home: float, p_away: float, total_goals: float) -> tuple[float, float]:
    """λh + λa = total_goals fixé ; bisection sur la part domicile pour coller à P(home) - P(away)."""
    lo, hi = 0.05, total_goals - 0.05
    target = p_home - p_away
    for _ in range(50):
        mid = (lo + hi) / 2
        h, _, a = _outcome_probs(_matrix(mid, total_goals - mid))
        if h - a < target:
            lo = mid
        else:
            hi = mid
    lh = (lo + hi) / 2
    return lh, total_goals - lh


def _sign(i: int, j: int) -> int:
    return (i > j) - (i < j)


def total_goals_from_market(over_odds: float | None, under_odds: float | None, line: float | None) -> float | None:
    """λ (total de buts) tel que P(Poisson(λ) > line) égale la probabilité implicite normalisée de l'over,
    par bissection — méthode `total_from_over` de backend/scripts/mesure_totals.py, mesurée dans
    docs/mesures/2026-09-11-score-le-plus-probable.md (complément du 11/09/2026). None si les cotes manquent,
    sont invalides (<=1), ou si la ligne n'est pas un multiple de 0,5 (une ligne entière laisse une masse de
    buts exactement sur la ligne, non gérée par cette formule ; ex. 2.0, 2.25, 2.75)."""
    if over_odds is None or under_odds is None or line is None:
        return None
    if over_odds <= 1 or under_odds <= 1:
        return None
    if abs((line % 1) - 0.5) > 1e-9:
        return None
    p_over_raw, p_under_raw = 1 / over_odds, 1 / under_odds
    p_over = p_over_raw / (p_over_raw + p_under_raw)
    k = math.floor(line)
    lo, hi = 0.2, 8.0
    for _ in range(60):
        mid = (lo + hi) / 2
        p = 1 - sum(_pois(mid, i) for i in range(k + 1))
        if p < p_over:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def expected_total(competition: str, totals_snapshot) -> tuple[float, str]:
    """Total de buts attendu pour le match : marché (dernier relevé over/under Pinnacle) si exploitable,
    repli sur la constante de ligue sinon. `totals_snapshot` est un objet portant `.over`, `.under`, `.line`
    (typiquement `app.models.totals_snapshot.TotalsSnapshot`), ou None si aucun relevé n'est disponible.
    Retourne (total, source) avec source "marché" ou "ligue"."""
    if totals_snapshot is not None:
        total = total_goals_from_market(totals_snapshot.over, totals_snapshot.under, totals_snapshot.line)
        if total is not None:
            return total, "marché"
    return LEAGUE_GOALS.get(competition, DEFAULT_GOALS), "ligue"


def most_probable_score(
    p_home: float | None, p_draw: float | None, p_away: float | None,
    total_goals: float, favourite: str,
) -> ScoreDistribution | None:
    if p_home is None or p_draw is None or p_away is None:
        return None
    lh, la = _fit_sum(p_home, p_away, total_goals)
    m = _matrix(lh, la)
    fav_sign = _FAVOURITE_SIGN[favourite]
    cells = [(i, j) for i in range(MAXG + 1) for j in range(MAXG + 1) if _sign(i, j) == fav_sign]
    ti, tj = max(cells, key=lambda t: m[t[0]][t[1]])
    top5 = sorted(((i, j) for i in range(MAXG + 1) for j in range(MAXG + 1)), key=lambda t: m[t[0]][t[1]], reverse=True)[:5]
    dist = tuple(ScoreProbability(f"{i}-{j}", m[i][j]) for i, j in top5)
    return ScoreDistribution(top=f"{ti}-{tj}", top_probability=m[ti][tj], distribution=dist, lambda_home=lh, lambda_away=la)
