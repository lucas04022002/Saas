"""Score le plus probable déduit du marché : Poisson calibré sur le 1N2, total de buts fixé par ligue.

Méthode et choix de la variante D (total de buts fixé, score cohérent avec le favori) mesurés dans
docs/mesures/2026-09-11-score-le-plus-probable.md — ne pas changer sans nouvelle mesure. Aucune prédiction :
c'est une traduction fidèle du marché en score, comme le reste du moteur.
"""
import math

from app.engine.types import ScoreDistribution, ScoreProbability

MAXG = 8

# Buts moyens par match, mesurés sur football-data.co.uk — sert de repli tant que le marché over/under n'est pas
# collecté. Top 5 : saison 2025/26. Championnats secondaires (mode gratuit, jamais de relevé over/under, donc
# TOUJOURS ce repli) : saisons 2024/25 + 2025/26 complètes, de 456 (SC0) à 1 104 (E1) matchs par ligue,
# mesurées le 22/09/2026. Sans entrée, l'Eredivisie (3,08) et la Serie B (2,51) auraient le même score.
# CL/EL/NL et toute compétition inconnue utilisent DEFAULT_GOALS.
LEAGUE_GOALS = {
    "E0": 2.75, "F1": 2.82, "SP1": 2.69, "D1": 3.24, "I1": 2.43,
    "E1": 2.53, "F2": 2.56, "SP2": 2.58, "D2": 2.98, "I2": 2.51,
    "N1": 3.08, "P1": 2.63, "B1": 2.72, "T1": 2.80, "G1": 2.51, "SC0": 2.87,
}
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


_TOTALS_MAX_GOALS = 15   # borne pratique de la bissection du total de buts (0..15) ; masse au-delà négligeable


def _line_components(line: float) -> list[tuple[float, float]] | None:
    """Décompose une ligne over/under en composantes (L_c, poids). Une ligne demie (x.5) ou entière (x.0) est
    une seule composante de poids 1 (l'entière est un push : X == L_c ne compte ni pour l'over ni pour
    l'under). Une ligne quart (x.25 / x.75) est réputée être deux paris de poids 0,5 chacun, sur l'entière et
    la demie qui l'encadrent (x.25 -> x.0 et x.5 ; x.75 -> x.5 et x.0 supérieur) — convention Asian handicap
    standard. None si la ligne n'est pas un multiple de 0,25."""
    quarters = line * 4
    if abs(quarters - round(quarters)) > 1e-9:
        return None
    frac4 = round(quarters) % 4
    if frac4 in (0, 2):   # entière ou demie
        return [(line, 1.0)]
    return [(line - 0.25, 0.5), (line + 0.25, 0.5)]   # quart : encadrée par l'entière et la demie voisines


def _over_under_probs(lam: float, c: float) -> tuple[float, float]:
    """P(X>c), P(X<c) pour X ~ Poisson(lam) sur 0..15 buts. c entier (push possible sur X==c, exclu des deux
    par la stricte inégalité) ou demi-entier (pas de push)."""
    lo, hi = math.floor(c), math.ceil(c)
    p_under = sum(_pois(lam, i) for i in range(0, hi))                          # i < c
    p_over = sum(_pois(lam, i) for i in range(lo + 1, _TOTALS_MAX_GOALS + 1))    # i > c
    return p_over, p_under


def total_goals_from_market(over_odds: float | None, under_odds: float | None, line: float | None) -> float | None:
    """λ (total de buts) tel que l'espérance de gain du pari Over, à la cote décimale équitable (sans marge)
    o = 1/p_over déduite du marché, soit nulle — par bissection (f croissante en λ). Une ligne quart (x.25,
    x.75) se décompose en deux demi-mises sur l'entière et la demie voisines (cf. `_line_components`), pour
    coller aux lignes réellement postées par Pinnacle (rarement x.5 : mesuré sur un relevé de 131 matchs,
    19 lignes à 2,5 contre 112 sur d'autres lignes). Mesuré dans docs/mesures/2026-09-11-score-le-plus-probable.md
    (complément du 11/09/2026). None si les cotes manquent, sont invalides (<=1), ou si la ligne n'est pas un
    multiple de 0,25."""
    if over_odds is None or under_odds is None or line is None:
        return None
    if over_odds <= 1 or under_odds <= 1:
        return None
    components = _line_components(line)
    if components is None:
        return None
    p_over_raw, p_under_raw = 1 / over_odds, 1 / under_odds
    p_over = p_over_raw / (p_over_raw + p_under_raw)
    fair_odds = 1 / p_over

    def f(lam: float) -> float:
        total = 0.0
        for c, w in components:
            p_o, p_u = _over_under_probs(lam, c)
            total += w * (p_o * (fair_odds - 1) - p_u)
        return total

    lo, hi = 0.2, 8.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) < 0:
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
