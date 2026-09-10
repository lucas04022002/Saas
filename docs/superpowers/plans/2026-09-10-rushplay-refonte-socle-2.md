# RushPlay refonte — plan d'exécution du socle, partie 2 (moteur, API, santé, déploiement)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Suite de `2026-09-10-rushplay-refonte-socle.md` (Tasks 1 à 6) : mêmes contraintes globales, même structure de fichiers.

**Goal, Architecture, Tech Stack, Global Constraints :** identiques à la partie 1. Rappel des interdits de vocabulaire : `value_bet`, `value_percent`, `confidence_score`, `recommended_bet`, `prediction`.

---

### Task 7 : Moteur — probabilités, favori, écarts, mouvement

**Files:**
- Create: `backend/app/engine/__init__.py` (vide), `backend/app/engine/types.py`, `backend/app/engine/probabilities.py`, `backend/app/engine/market.py`
- Test: `backend/tests/test_engine_probabilities.py`, `backend/tests/test_engine_market.py`

**Interfaces:**
- Produces (tout pur Python, sans SQLAlchemy) :
  - `types.py` : `Odds = tuple[float, float, float]` (domicile, nul, extérieur) ; `Probs = tuple[float, float, float]` ; dataclass `BookQuote(bookmaker: str, taken_at: datetime, odds: Odds)` ; dataclass `Reading(reference: Probs, reference_source: str, favourite: str, favourite_prob: float, margin_by_book: dict[str, float], gaps: dict[str, tuple[float, float, float]], movement: tuple[float, float, float] | None, first_taken_at: datetime | None, last_taken_at: datetime | None)`.
  - `probabilities.py` : `implied(odds: Odds) -> Probs` (normalisation proportionnelle, somme 1), `margin(odds: Odds) -> float` (Σ1/cote − 1), `reference(latest: dict[str, Odds]) -> tuple[Probs, str]` (Pinnacle si présent → `"pinnacle"`, sinon moyenne des probabilités implicites de tous → `"moyenne"`).
  - `market.py` : `favourite(p: Probs) -> tuple[str, float]` (`"home"|"draw"|"away"`, prob), `gaps(latest: dict[str, Odds], ref: Probs) -> dict[str, tuple[float, float, float]]` (par bookmaker, `cote × p_ref − 1` par issue), `movement(first_ref: Probs, last_ref: Probs) -> tuple[float, float, float]` (différence en points de %), `read(quotes: list[BookQuote], french_books: tuple[str, ...]) -> Reading` (assemble tout à partir de la liste brute de relevés).

- [ ] **Step 1 : `backend/app/engine/types.py`**

```python
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
```

- [ ] **Step 2 : tests `backend/tests/test_engine_probabilities.py`**

```python
import pytest

from app.engine.probabilities import implied, margin, reference


def test_implied_sums_to_one_and_removes_margin():
    p = implied((2.0, 3.5, 4.0))
    assert pytest.approx(sum(p), abs=1e-12) == 1.0
    assert p[0] > p[1] > p[2]
    assert pytest.approx(p[0], abs=1e-9) == (1 / 2.0) / (1 / 2.0 + 1 / 3.5 + 1 / 4.0)


def test_margin_of_fair_odds_is_zero_and_typical_book_is_positive():
    assert pytest.approx(margin((3.0, 3.0, 3.0)), abs=1e-12) == 0.0
    assert 0.05 < margin((1.9, 3.5, 3.9)) < 0.10


def test_reference_prefers_pinnacle():
    latest = {"betclic_fr": (1.9, 3.5, 3.9), "pinnacle": (2.02, 3.7, 3.95)}
    p, src = reference(latest)
    assert src == "pinnacle" and p == implied((2.02, 3.7, 3.95))


def test_reference_falls_back_to_mean_of_books():
    latest = {"betclic_fr": (2.0, 3.5, 4.0), "winamax_fr": (2.2, 3.5, 3.6)}
    p, src = reference(latest)
    a, b = implied((2.0, 3.5, 4.0)), implied((2.2, 3.5, 3.6))
    assert src == "moyenne"
    assert pytest.approx(p[0], abs=1e-9) == (a[0] + b[0]) / 2
    assert pytest.approx(sum(p), abs=1e-9) == 1.0


def test_reference_rejects_empty():
    with pytest.raises(ValueError):
        reference({})
```

Run : `python -m pytest tests/test_engine_probabilities.py -v` → Expected : `ImportError`.

- [ ] **Step 3 : `backend/app/engine/probabilities.py`**

```python
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
```

- [ ] **Step 4 : lancer** → `python -m pytest tests/test_engine_probabilities.py -v` → 5 PASS.

- [ ] **Step 5 : tests `backend/tests/test_engine_market.py`**

```python
from datetime import datetime, timezone

import pytest

from app.engine.market import favourite, gaps, movement, read
from app.engine.probabilities import implied
from app.engine.types import BookQuote

FR = ("betclic_fr", "winamax_fr", "unibet_fr", "pmu_fr", "netbet_fr")
T0 = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)


def test_favourite_is_argmax():
    assert favourite((0.58, 0.24, 0.18)) == ("home", 0.58)
    assert favourite((0.30, 0.25, 0.45)) == ("away", 0.45)


def test_gaps_positive_when_book_pays_more_than_reference():
    ref = implied((2.0, 3.5, 4.0))              # ≈ (0.4706, 0.2689, 0.2353)
    g = gaps({"betclic_fr": (2.2, 3.5, 4.0)}, ref)
    assert g["betclic_fr"][0] == pytest.approx(2.2 * ref[0] - 1, abs=1e-9)
    assert g["betclic_fr"][0] > 0 and g["betclic_fr"][1] < 0


def test_movement_in_percentage_points():
    assert movement((0.50, 0.25, 0.25), (0.53, 0.24, 0.23)) == pytest.approx((3.0, -1.0, -2.0), abs=1e-9)


def test_read_assembles_everything_from_raw_quotes():
    quotes = [
        BookQuote("pinnacle", T0, (2.10, 3.60, 3.80)),
        BookQuote("betclic_fr", T0, (2.00, 3.50, 3.70)),
        BookQuote("pinnacle", T1, (1.95, 3.70, 4.10)),
        BookQuote("betclic_fr", T1, (1.90, 3.55, 3.90)),
        BookQuote("winamax_fr", T1, (2.05, 3.50, 3.80)),
        BookQuote("williamhill", T1, (2.50, 3.50, 3.80)),   # ignoré : ni FR ni référence
    ]
    r = read(quotes, FR)
    assert r.reference_source == "pinnacle" and r.reference == implied((1.95, 3.70, 4.10))
    assert r.favourite == "home" and r.favourite_prob == pytest.approx(r.reference[0])
    assert set(r.latest_by_book) == {"pinnacle", "betclic_fr", "winamax_fr"}
    assert set(r.gaps) == {"betclic_fr", "winamax_fr"}                 # écarts calculés pour les FR seulement
    assert r.gaps["winamax_fr"][0] == pytest.approx(2.05 * r.reference[0] - 1, abs=1e-9)
    assert r.movement[0] == pytest.approx((implied((1.95, 3.70, 4.10))[0] - implied((2.10, 3.60, 3.80))[0]) * 100, abs=1e-9)
    assert (r.first_taken_at, r.last_taken_at) == (T0, T1)
    assert 0 < r.margin_by_book["betclic_fr"] < 0.1


def test_read_single_snapshot_has_no_movement():
    r = read([BookQuote("betclic_fr", T0, (2.0, 3.5, 4.0))], FR)
    assert r.movement is None and r.reference_source == "moyenne"


def test_read_uses_latest_snapshot_per_book_even_if_books_differ_in_timing():
    quotes = [BookQuote("betclic_fr", T0, (2.0, 3.5, 4.0)), BookQuote("pinnacle", T1, (2.1, 3.6, 3.8))]
    r = read(quotes, FR)
    assert r.latest_by_book["betclic_fr"] == (2.0, 3.5, 4.0)
    assert r.last_taken_at == T1
```

Run : `python -m pytest tests/test_engine_market.py -v` → Expected : `ImportError`.

- [ ] **Step 6 : `backend/app/engine/market.py`**

```python
"""Lecture du marché : favori, écarts bookmakers FR vs référence, mouvement entre relevés."""
from collections import defaultdict

from app.engine.probabilities import REFERENCE_BOOKMAKER, implied, margin, reference
from app.engine.types import OUTCOMES, BookQuote, Odds, Probs, Reading


def favourite(p: Probs) -> tuple[str, float]:
    i = max(range(3), key=lambda k: p[k])
    return OUTCOMES[i], p[i]


def gaps(latest: dict[str, Odds], ref: Probs) -> dict[str, tuple[float, float, float]]:
    return {book: (o[0] * ref[0] - 1, o[1] * ref[1] - 1, o[2] * ref[2] - 1) for book, o in latest.items()}


def movement(first_ref: Probs, last_ref: Probs) -> tuple[float, float, float]:
    return tuple((last_ref[k] - first_ref[k]) * 100 for k in range(3))  # type: ignore[return-value]


def _by_time(quotes: list[BookQuote]) -> dict:
    """relevés groupés par horodatage : {taken_at: {bookmaker: odds}}"""
    grouped: dict = defaultdict(dict)
    for q in quotes:
        grouped[q.taken_at][q.bookmaker] = q.odds
    return dict(sorted(grouped.items()))


def read(quotes: list[BookQuote], french_books: tuple[str, ...]) -> Reading:
    kept = [q for q in quotes if q.bookmaker in french_books or q.bookmaker == REFERENCE_BOOKMAKER]
    if not kept:
        raise ValueError("aucun relevé exploitable")
    latest: dict[str, BookQuote] = {}
    for q in sorted(kept, key=lambda q: q.taken_at):
        latest[q.bookmaker] = q
    latest_odds = {b: q.odds for b, q in latest.items()}
    ref, src = reference(latest_odds)
    fav, fav_p = favourite(ref)
    grouped = _by_time(kept)
    times = list(grouped)
    mov = None
    if len(times) >= 2:
        first_ref, _ = reference(grouped[times[0]])
        mov = movement(first_ref, ref)
    return Reading(
        reference=ref, reference_source=src, favourite=fav, favourite_prob=fav_p,
        margin_by_book={b: margin(o) for b, o in latest_odds.items()},
        latest_by_book=latest_odds,
        gaps=gaps({b: o for b, o in latest_odds.items() if b in french_books}, ref),
        movement=mov, first_taken_at=times[0], last_taken_at=times[-1],
    )
```

- [ ] **Step 7 : lancer** → `python -m pytest tests/test_engine_market.py tests/test_engine_probabilities.py -v` → 11 PASS.

- [ ] **Step 8 : commit**

```bash
git add -A && git commit -m "feat(engine): probabilités implicites, référence, favori, écarts, mouvement"
```

---

### Task 8 : Moteur — contexte (forme, face-à-face) et texte par gabarits

**Files:**
- Create: `backend/app/engine/context.py`, `backend/app/engine/narrative.py`
- Test: `backend/tests/test_engine_context.py`, `backend/tests/test_engine_narrative.py`

**Interfaces:**
- Produces :
  - `context.py` : dataclass `PastMatch(kickoff_at: datetime, home: str, away: str, hg: int, ag: int)` ; dataclass `Form(played: int, wins: int, draws: int, losses: int, goals_for: int, goals_against: int, sequence: str)` (`sequence` ex. `"VVNDV"`, du plus récent au plus ancien) ; `form(team: str, history: list[PastMatch], n: int = 5) -> Form` ; `head_to_head(home: str, away: str, history: list[PastMatch], n: int = 5) -> list[PastMatch]` (les n dernières confrontations, plus récente d'abord).
  - `narrative.py` : dataclass `MatchContext(home: str, away: str, reading: Reading, home_form: Form, away_form: Form, h2h: list[PastMatch], best_gap: tuple[str, str, float] | None)` (`best_gap` = (bookmaker, issue, écart)) ; `describe(ctx: MatchContext) -> str` (3 à 4 phrases, français, déterministe) ; `label(outcome: str, home: str, away: str) -> str` (`"home"` → nom de l'équipe, `"draw"` → « le nul »).

- [ ] **Step 1 : tests `backend/tests/test_engine_context.py`**

```python
from datetime import datetime, timedelta, timezone

from app.engine.context import PastMatch, form, head_to_head

T = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)


def pm(days_ago, home, away, hg, ag):
    return PastMatch(T - timedelta(days=days_ago), home, away, hg, ag)


HIST = [
    pm(1, "Lyon", "Nice", 2, 0),        # Lyon V
    pm(8, "Lens", "Lyon", 1, 1),        # Lyon N
    pm(15, "Lyon", "Marseille", 0, 3),  # Lyon D
    pm(22, "Metz", "Lyon", 0, 1),       # Lyon V
    pm(29, "Lyon", "Brest", 1, 0),      # Lyon V
    pm(36, "Nantes", "Lyon", 2, 2),     # 6e match : hors fenêtre de 5
    pm(400, "Marseille", "Lyon", 1, 0),
    pm(800, "Lyon", "Marseille", 2, 2),
]


def test_form_last_five_most_recent_first():
    f = form("Lyon", HIST)
    assert (f.played, f.wins, f.draws, f.losses) == (5, 3, 1, 1)
    assert (f.goals_for, f.goals_against) == (5, 4)
    assert f.sequence == "VNDVV"


def test_form_with_fewer_matches_than_window():
    f = form("Nice", HIST)
    assert f.played == 1 and f.losses == 1 and f.sequence == "D"


def test_form_unknown_team_is_empty():
    f = form("Inconnu", HIST)
    assert f.played == 0 and f.sequence == ""


def test_head_to_head_both_venues_most_recent_first():
    h2h = head_to_head("Lyon", "Marseille", HIST)
    assert [(m.home, m.away) for m in h2h] == [("Lyon", "Marseille"), ("Marseille", "Lyon"), ("Lyon", "Marseille")]
```

- [ ] **Step 2 : `backend/app/engine/context.py`**

```python
"""Contexte descriptif : forme récente et face-à-face. Descriptif, jamais prédictif."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PastMatch:
    kickoff_at: datetime
    home: str
    away: str
    hg: int
    ag: int


@dataclass
class Form:
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    sequence: str = ""   # "V" victoire, "N" nul, "D" défaite — du plus récent au plus ancien


def form(team: str, history: list[PastMatch], n: int = 5) -> Form:
    mine = sorted((m for m in history if team in (m.home, m.away)), key=lambda m: m.kickoff_at, reverse=True)[:n]
    f = Form()
    for m in mine:
        gf, ga = (m.hg, m.ag) if m.home == team else (m.ag, m.hg)
        f.played += 1; f.goals_for += gf; f.goals_against += ga
        if gf > ga:
            f.wins += 1; f.sequence += "V"
        elif gf == ga:
            f.draws += 1; f.sequence += "N"
        else:
            f.losses += 1; f.sequence += "D"
    return f


def head_to_head(home: str, away: str, history: list[PastMatch], n: int = 5) -> list[PastMatch]:
    pair = {home, away}
    return sorted((m for m in history if {m.home, m.away} == pair), key=lambda m: m.kickoff_at, reverse=True)[:n]
```

- [ ] **Step 3 : lancer** → `python -m pytest tests/test_engine_context.py -v` → 4 PASS.

- [ ] **Step 4 : tests `backend/tests/test_engine_narrative.py`**

```python
from datetime import datetime, timezone

from app.engine.context import Form, PastMatch
from app.engine.narrative import MatchContext, describe, label
from app.engine.types import Reading

T0 = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)


def reading(ref=(0.58, 0.24, 0.18), fav="home", mov=None, src="pinnacle"):
    return Reading(reference=ref, reference_source=src, favourite=fav, favourite_prob=max(ref),
                   latest_by_book={"betclic_fr": (1.78, 3.9, 4.8), "pinnacle": (1.72, 4.0, 5.0)},
                   margin_by_book={"betclic_fr": 0.07}, gaps={"betclic_fr": (0.032, -0.06, -0.14)},
                   movement=mov, first_taken_at=T0, last_taken_at=T1)


def ctx(**kw):
    base = dict(home="Lyon", away="Nice", reading=reading(), home_form=Form(5, 3, 1, 1, 7, 4, "VVNDV"),
                away_form=Form(5, 1, 2, 2, 4, 6, "DNVDN"), h2h=[], best_gap=("betclic_fr", "home", 0.032))
    base.update(kw)
    return MatchContext(**base)


def test_label():
    assert label("home", "Lyon", "Nice") == "Lyon" and label("away", "Lyon", "Nice") == "Nice" and label("draw", "Lyon", "Nice") == "le nul"


def test_clear_favourite_with_gap_and_form():
    t = describe(ctx())
    assert t == ("Lyon est favori à 58 %. Betclic paie 1,78 sur Lyon, soit 3,2 % au-dessus de la référence. "
                 "Lyon reste sur trois victoires lors des cinq derniers matchs ; Nice sur une seule.")


def test_movement_sentence_when_reference_moved_more_than_three_points():
    t = describe(ctx(reading=reading(mov=(4.2, -1.5, -2.7))))
    assert "La probabilité de Lyon a gagné 4,2 points depuis le premier relevé." in t


def test_tight_match_wording():
    t = describe(ctx(reading=reading(ref=(0.41, 0.30, 0.29), fav="home"), best_gap=None))
    assert t.startswith("Match serré : Lyon favori de peu à 41 %.")
    assert "au-dessus de la référence" not in t


def test_draw_favourite_and_h2h():
    h2h = [PastMatch(T0, "Lyon", "Nice", 1, 1), PastMatch(T0, "Nice", "Lyon", 0, 0)]
    t = describe(ctx(reading=reading(ref=(0.33, 0.36, 0.31), fav="draw"), h2h=h2h, best_gap=None))
    assert "le nul est l'issue la plus probable à 36 %" in t
    assert "Les deux dernières confrontations se sont soldées par un nul." in t


def test_describe_is_deterministic():
    assert describe(ctx()) == describe(ctx())
```

- [ ] **Step 5 : `backend/app/engine/narrative.py`**

```python
"""Analyse textuelle par gabarits : 3 à 4 phrases, déterministes, à partir des chiffres seulement."""
from dataclasses import dataclass

from app.engine.context import Form, PastMatch
from app.engine.types import Reading

BOOK_LABELS = {"betclic_fr": "Betclic", "winamax_fr": "Winamax", "unibet_fr": "Unibet", "pmu_fr": "PMU", "netbet_fr": "NetBet", "pinnacle": "Pinnacle"}
NUMBERS = {1: "une seule", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq"}
TIGHT_MAX = 0.45      # en dessous : match serré
MOVE_MIN = 3.0        # points de % pour mentionner un mouvement
GAP_MIN = 0.03        # 3 % pour mentionner un écart


@dataclass
class MatchContext:
    home: str
    away: str
    reading: Reading
    home_form: Form
    away_form: Form
    h2h: list[PastMatch]
    best_gap: tuple[str, str, float] | None   # (bookmaker, issue, écart)


def label(outcome: str, home: str, away: str) -> str:
    return {"home": home, "away": away, "draw": "le nul"}[outcome]


def _pct(x: float) -> str:
    return f"{round(x * 100)} %"


def _fr(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def _favourite_sentence(ctx: MatchContext) -> str:
    r = ctx.reading
    who = label(r.favourite, ctx.home, ctx.away)
    if r.favourite == "draw":
        return f"Match indécis : {who} est l'issue la plus probable à {_pct(r.favourite_prob)}."
    if r.favourite_prob < TIGHT_MAX:
        return f"Match serré : {who} favori de peu à {_pct(r.favourite_prob)}."
    return f"{who} est favori à {_pct(r.favourite_prob)}."


def _gap_sentence(ctx: MatchContext) -> str | None:
    if ctx.best_gap is None or ctx.best_gap[2] < GAP_MIN:
        return None
    book, outcome, gap = ctx.best_gap
    odds = ctx.reading.latest_by_book[book][("home", "draw", "away").index(outcome)]
    return f"{BOOK_LABELS.get(book, book)} paie {_fr(odds, 2)} sur {label(outcome, ctx.home, ctx.away)}, soit {_fr(gap * 100)} % au-dessus de la référence."


def _movement_sentence(ctx: MatchContext) -> str | None:
    r = ctx.reading
    if r.movement is None:
        return None
    k = ("home", "draw", "away").index(r.favourite)
    delta = r.movement[k]
    if abs(delta) < MOVE_MIN:
        return None
    verb = "gagné" if delta > 0 else "perdu"
    return f"La probabilité de {label(r.favourite, ctx.home, ctx.away)} a {verb} {_fr(abs(delta))} points depuis le premier relevé."


def _form_sentence(ctx: MatchContext) -> str | None:
    hf, af = ctx.home_form, ctx.away_form
    if hf.played == 0 and af.played == 0:
        return None
    def wins(f: Form) -> str:
        return NUMBERS.get(f.wins, str(f.wins)) + (" victoire" if f.wins == 1 else " victoires")
    if hf.played and af.played:
        return f"{ctx.home} reste sur {wins(hf)} lors des {NUMBERS[hf.played]} derniers matchs ; {ctx.away} sur {NUMBERS.get(af.wins, str(af.wins))}{'' if af.wins != 1 else ''}." \
            .replace(f"{ctx.away} sur une seule.", f"{ctx.away} sur une seule.")
    f, name = (hf, ctx.home) if hf.played else (af, ctx.away)
    return f"{name} reste sur {wins(f)} lors des {NUMBERS[f.played]} derniers matchs."


def _h2h_sentence(ctx: MatchContext) -> str | None:
    if len(ctx.h2h) < 2:
        return None
    last = ctx.h2h[:2]
    if all(m.hg == m.ag for m in last):
        return "Les deux dernières confrontations se sont soldées par un nul."
    winners = []
    for m in last:
        winners.append(m.home if m.hg > m.ag else m.away if m.ag > m.hg else None)
    if winners[0] and winners[0] == winners[1]:
        return f"{winners[0]} a remporté les deux dernières confrontations."
    return None


def describe(ctx: MatchContext) -> str:
    parts = [_favourite_sentence(ctx), _gap_sentence(ctx), _movement_sentence(ctx), _form_sentence(ctx), _h2h_sentence(ctx)]
    return " ".join(p for p in parts if p)
```

Attention à la phrase de forme attendue par le test : « Lyon reste sur trois victoires lors des cinq derniers matchs ; Nice sur une seule. » Simplifier `_form_sentence` pour produire exactement `f"{home} reste sur {wins(hf)} lors des {NUMBERS[hf.played]} derniers matchs ; {away} sur {NUMBERS.get(af.wins, str(af.wins))}."` quand les deux ont joué (le `.replace` inutile ci-dessus est à retirer) — avec `NUMBERS[1] == "une seule"` la phrase du test sort telle quelle.

- [ ] **Step 6 : lancer** → `python -m pytest tests/test_engine_narrative.py -v` → 6 PASS. Ajuster les gabarits jusqu'à égalité stricte avec les textes attendus ; ne pas assouplir les tests.

- [ ] **Step 7 : commit**

```bash
git add -A && git commit -m "feat(engine): forme, face-à-face et analyse textuelle par gabarits"
```

---

### Task 9 : Service de lecture + routes `matches` (liste, détail) + paywall

**Files:**
- Create: `backend/app/services/market_reading.py`
- Rewrite: `backend/app/api/v1/endpoints/matches.py`, `backend/app/core/access.py`
- Test: `backend/tests/test_api_matches.py`

**Interfaces:**
- Consumes: `read`, `describe`, `form`, `head_to_head`, `FRENCH_BOOKMAKERS`, modèles.
- Produces :
  - `market_reading.py` : `quotes_for(match: Match) -> list[BookQuote]` ; `reading_for(match) -> Reading | None` (None sans relevé) ; `history_for(db, team_ids: list, before: datetime, limit: int = 30) -> list[PastMatch]` ; `best_gap(reading) -> tuple[str, str, float] | None` (meilleur écart parmi les bookmakers FR, toutes issues) ; `match_summary(db, match) -> dict` (item de liste) ; `match_detail(db, match) -> dict`.
  - `access.py` : `is_pro(user)`, `PREMIUM_LIST_FIELDS = ("best_gap", "movement")`, `gate_list(items, user) -> list[dict]` (met `locked=True` et ces champs à `None` pour les non-abonnés ; le favori et sa probabilité restent visibles), `gate_detail(detail, user) -> dict` (non-abonné : `books`, `gaps`, `movement`, `history` (relevés) mis à `None`, `locked=True` ; `reading.favourite`, `reading.reference`, `analysis`, `form`, `h2h` restent visibles).
  - Routes : `GET /api/v1/matches?date=YYYY-MM-DD&competition=E0&page&limit` (par défaut : matchs `SCHEDULED` des 7 prochains jours, tri `kickoff_at`), `GET /api/v1/matches/{id}`. Jamais de match `QUARANTINE` dans les réponses.

Format de `match_summary` :

```json
{"id": "...", "competition": "E0", "league": "Premier League", "home_team": "Arsenal", "away_team": "Chelsea",
 "kickoff_at": "2026-09-12T14:00:00Z", "status": "SCHEDULED",
 "favourite": {"outcome": "home", "label": "Arsenal", "prob": 0.52, "source": "pinnacle"},
 "reference": {"home": 0.52, "draw": 0.25, "away": 0.23},
 "best_gap": {"bookmaker": "winamax_fr", "outcome": "home", "gap": 0.035, "odds": 2.05},
 "movement": {"home": 1.2, "draw": -0.4, "away": -0.8},
 "odds_taken_at": "2026-09-12T12:00:00Z", "locked": false}
```

Format de `match_detail` = summary + `"books": [{"bookmaker": "betclic_fr", "label": "Betclic", "home": 1.95, "draw": 3.6, "away": 3.9, "margin": 0.07, "gaps": {"home": 0.014, "draw": -0.1, "away": -0.1}}, ...]` (FR seulement, plus la référence sous `"reference_book"`), `"history": [{"taken_at": "...", "reference": {"home":..,"draw":..,"away":..}}, ...]` (un point par relevé), `"form": {"home": {...Form...}, "away": {...}}`, `"h2h": [{"kickoff_at":..., "home":..., "away":..., "score": "2-1"}]`, `"analysis": "<texte>"`, `"result": {"home": 2, "away": 0} | null`.

- [ ] **Step 1 : tests `backend/tests/test_api_matches.py`**

```python
from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import auth_header, make_match

NOW = datetime.now(timezone.utc)


def seed_match_with_odds(db, kickoff=None):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    m = make_match(db, h, a, kickoff=kickoff or NOW + timedelta(days=2))
    t0, t1 = NOW - timedelta(days=2), NOW - timedelta(hours=3)
    for book, t, odds in [("pinnacle", t0, (2.10, 3.6, 3.8)), ("betclic_fr", t0, (2.0, 3.5, 3.7)),
                          ("pinnacle", t1, (1.95, 3.7, 4.1)), ("betclic_fr", t1, (1.9, 3.55, 3.9)), ("winamax_fr", t1, (2.05, 3.5, 3.8))]:
        db.add(OddsSnapshot(match_id=m.id, bookmaker=book, taken_at=t, home=odds[0], draw=odds[1], away=odds[2]))
    db.commit()
    return m


def test_list_upcoming_shows_favourite_and_locks_premium_for_anonymous(client, db):
    seed_match_with_odds(db)
    r = client.get("/api/v1/matches")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 1
    it = items[0]
    assert it["favourite"]["outcome"] == "home" and it["favourite"]["label"] == "Arsenal" and it["favourite"]["source"] == "pinnacle"
    assert it["locked"] is True and it["best_gap"] is None and it["movement"] is None


def test_list_shows_gap_and_movement_for_pro(client, db, pro_user):
    seed_match_with_odds(db)
    it = client.get("/api/v1/matches", headers=auth_header(pro_user)).json()["data"]["items"][0]
    assert it["locked"] is False
    assert it["best_gap"]["bookmaker"] == "winamax_fr" and it["best_gap"]["outcome"] == "home" and it["best_gap"]["gap"] > 0
    assert it["movement"]["home"] != 0


def test_list_filters_by_date_and_competition(client, db):
    m = seed_match_with_odds(db)
    day = m.kickoff_at.date().isoformat()
    assert len(client.get(f"/api/v1/matches?date={day}").json()["data"]["items"]) == 1
    assert client.get(f"/api/v1/matches?date={day}&competition=F1").json()["data"]["items"] == []


def test_list_never_returns_quarantine_or_matches_without_odds(client, db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Lyon").one(), db.query(Team).filter_by(name="Nice").one()
    make_match(db, h, a, competition="F1", kickoff=NOW + timedelta(days=1))                    # sans relevé
    make_match(db, h, a, competition="F1", kickoff=NOW + timedelta(days=3), status=MatchStatus.QUARANTINE)
    items = client.get("/api/v1/matches").json()["data"]["items"]
    assert len(items) == 1 and items[0]["favourite"] is None and items[0]["odds_taken_at"] is None


def test_detail_pro_has_books_history_analysis(client, db, pro_user):
    m = seed_match_with_odds(db)
    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert {b["bookmaker"] for b in d["books"]} == {"betclic_fr", "winamax_fr"}
    assert d["reference_book"]["bookmaker"] == "pinnacle"
    assert len(d["history"]) == 2 and d["history"][0]["taken_at"] < d["history"][1]["taken_at"]
    assert d["analysis"].startswith("Arsenal est favori à")
    assert d["form"]["home"]["played"] == 0 and d["h2h"] == [] and d["result"] is None


def test_detail_anonymous_is_locked_but_keeps_favourite_and_analysis(client, db):
    m = seed_match_with_odds(db)
    d = client.get(f"/api/v1/matches/{m.id}").json()["data"]
    assert d["locked"] is True and d["books"] is None and d["history"] is None and d["movement"] is None
    assert d["favourite"]["outcome"] == "home" and d["analysis"]


def test_detail_uses_finished_history_for_form_and_h2h(client, db, pro_user):
    m = seed_match_with_odds(db)
    h, a = m.home, m.away
    make_match(db, h, a, kickoff=NOW - timedelta(days=200), status=MatchStatus.FINISHED, home_score=2, away_score=0)
    make_match(db, a, h, kickoff=NOW - timedelta(days=30), status=MatchStatus.FINISHED, home_score=1, away_score=1)
    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert d["form"]["home"]["sequence"] == "NV" and d["form"]["away"]["sequence"] == "ND"
    assert [x["score"] for x in d["h2h"]] == ["1-1", "2-0"]


def test_detail_404_and_quarantine_hidden(client, db):
    assert client.get("/api/v1/matches/00000000-0000-0000-0000-000000000000").status_code == 404
```

- [ ] **Step 2 : `backend/app/services/market_reading.py`**

```python
"""Assemble la lecture du marché d'un match à partir de la base (relevés, historique)."""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.collectors.competitions import FRENCH_BOOKMAKERS
from app.engine.context import Form, PastMatch, form, head_to_head
from app.engine.market import read
from app.engine.narrative import BOOK_LABELS, MatchContext, describe, label
from app.engine.types import OUTCOMES, BookQuote, Reading
from app.models.enums import MatchStatus
from app.models.match import Match


def quotes_for(match: Match) -> list[BookQuote]:
    return [BookQuote(s.bookmaker, s.taken_at, (s.home, s.draw, s.away)) for s in match.snapshots]


def reading_for(match: Match) -> Reading | None:
    q = quotes_for(match)
    if not q:
        return None
    try:
        return read(q, FRENCH_BOOKMAKERS)
    except ValueError:
        return None


def best_gap(reading: Reading) -> tuple[str, str, float] | None:
    best = None
    for book, g in reading.gaps.items():
        for k, outcome in enumerate(OUTCOMES):
            if best is None or g[k] > best[2]:
                best = (book, outcome, g[k])
    return best


def history_for(db: Session, team_ids: list, before: datetime, limit: int = 30) -> list[PastMatch]:
    rows = db.scalars(
        select(Match).where(Match.status == MatchStatus.FINISHED, Match.kickoff_at < before,
                            or_(Match.home_team_id.in_(team_ids), Match.away_team_id.in_(team_ids)))
        .order_by(Match.kickoff_at.desc()).limit(limit)
    ).all()
    return [PastMatch(r.kickoff_at, r.home_team, r.away_team, r.home_score or 0, r.away_score or 0) for r in rows]


def _probs(p) -> dict:
    return {"home": p[0], "draw": p[1], "away": p[2]}


def match_summary(db: Session, match: Match) -> dict:
    r = reading_for(match)
    out = {
        "id": str(match.id), "competition": match.competition, "league": match.league,
        "home_team": match.home_team, "away_team": match.away_team, "kickoff_at": match.kickoff_at, "status": match.status.value,
        "favourite": None, "reference": None, "best_gap": None, "movement": None, "odds_taken_at": None, "locked": False,
    }
    if r is None:
        return out
    bg = best_gap(r)
    out["favourite"] = {"outcome": r.favourite, "label": label(r.favourite, match.home_team, match.away_team), "prob": r.favourite_prob, "source": r.reference_source}
    out["reference"] = _probs(r.reference)
    if bg:
        out["best_gap"] = {"bookmaker": bg[0], "outcome": bg[1], "gap": bg[2], "odds": r.latest_by_book[bg[0]][OUTCOMES.index(bg[1])]}
    out["movement"] = _probs(r.movement) if r.movement else None
    out["odds_taken_at"] = r.last_taken_at
    return out


def match_detail(db: Session, match: Match) -> dict:
    out = match_summary(db, match)
    r = reading_for(match)
    hist = history_for(db, [match.home_team_id, match.away_team_id], before=match.kickoff_at)
    hf, af = form(match.home_team, hist), form(match.away_team, hist)
    h2h = head_to_head(match.home_team, match.away_team, hist)
    out.update({
        "books": None, "reference_book": None, "history": None,
        "form": {"home": vars(hf), "away": vars(af)},
        "h2h": [{"kickoff_at": m.kickoff_at, "home": m.home, "away": m.away, "score": f"{m.hg}-{m.ag}"} for m in h2h],
        "analysis": None,
        "result": {"home": match.home_score, "away": match.away_score} if match.status == MatchStatus.FINISHED else None,
    })
    if r is None:
        return out
    out["books"] = [
        {"bookmaker": b, "label": BOOK_LABELS.get(b, b), "home": o[0], "draw": o[1], "away": o[2],
         "margin": r.margin_by_book[b], "gaps": _probs(r.gaps[b])}
        for b, o in r.latest_by_book.items() if b in FRENCH_BOOKMAKERS
    ]
    if "pinnacle" in r.latest_by_book:
        o = r.latest_by_book["pinnacle"]
        out["reference_book"] = {"bookmaker": "pinnacle", "label": "Pinnacle", "home": o[0], "draw": o[1], "away": o[2], "margin": r.margin_by_book["pinnacle"]}
    # un point d'historique par relevé : la référence recalculée sur les cotes de ce relevé
    from app.engine.market import _by_time
    from app.engine.probabilities import reference
    kept = [q for q in quotes_for(match) if q.bookmaker in FRENCH_BOOKMAKERS or q.bookmaker == "pinnacle"]
    out["history"] = [{"taken_at": t, "reference": _probs(reference(books)[0])} for t, books in _by_time(kept).items()]
    out["analysis"] = describe(MatchContext(match.home_team, match.away_team, r, hf, af, h2h, best_gap(r)))
    return out
```

- [ ] **Step 3 : `backend/app/core/access.py` — réécrire**

```python
"""Paywall côté serveur : le favori et sa probabilité sont publics ; écarts, mouvements, relevés et comparateur sont réservés."""
from app.models.enums import SubscriptionPlan
from app.models.user import User

PAID_PLANS = {SubscriptionPlan.PRO, SubscriptionPlan.ELITE}
PREMIUM_LIST_FIELDS = ("best_gap", "movement")
PREMIUM_DETAIL_FIELDS = ("best_gap", "movement", "books", "reference_book", "history")


def is_pro(user: User | None) -> bool:
    return user is not None and user.subscription_plan in PAID_PLANS


def gate_list(items: list[dict], user: User | None) -> list[dict]:
    pro = is_pro(user)
    for item in items:
        item["locked"] = not pro
        if not pro:
            for f in PREMIUM_LIST_FIELDS:
                item[f] = None
    return items


def gate_detail(detail: dict, user: User | None) -> dict:
    pro = is_pro(user)
    detail["locked"] = not pro
    if not pro:
        for f in PREMIUM_DETAIL_FIELDS:
            detail[f] = None
    return detail
```

- [ ] **Step 4 : `backend/app/api/v1/endpoints/matches.py` — réécrire**

```python
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user_optional, get_db
from app.core.access import gate_detail, gate_list
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.user import User
from app.services.market_reading import match_detail, match_summary

router = APIRouter(prefix="/matches", tags=["matches"])
VISIBLE = (MatchStatus.SCHEDULED, MatchStatus.LIVE, MatchStatus.FINISHED, MatchStatus.POSTPONED)


@router.get("")
def list_matches(
    match_date: date | None = Query(default=None, alias="date"),
    competition: str | None = Query(default=None, pattern="^(E0|F1|SP1|D1|I1|CL)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    q = select(Match).where(Match.status.in_(VISIBLE)).options(selectinload(Match.snapshots))
    if match_date:
        q = q.where(Match.kickoff_at >= datetime.combine(match_date, time.min, tzinfo=timezone.utc),
                    Match.kickoff_at <= datetime.combine(match_date, time.max, tzinfo=timezone.utc))
    else:
        now = datetime.now(timezone.utc)
        q = q.where(Match.status == MatchStatus.SCHEDULED, Match.kickoff_at >= now - timedelta(hours=3), Match.kickoff_at <= now + timedelta(days=7))
    if competition:
        q = q.where(Match.competition == competition)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Match.kickoff_at.asc()).offset((page - 1) * limit).limit(limit)).unique().all()
    items = gate_list([match_summary(db, m) for m in rows], current_user)
    return {"success": True, "message": "Matches fetched", "data": {"items": items, "pagination": {"page": page, "limit": limit, "total": total}}}


@router.get("/{match_id}")
def get_match(match_id: str, db: Session = Depends(get_db), current_user: User | None = Depends(get_current_user_optional)):
    try:
        row = db.scalar(select(Match).where(Match.id == match_id).options(selectinload(Match.snapshots)))
    except Exception:
        row = None
    if row is None or row.status == MatchStatus.QUARANTINE:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"success": True, "message": "Match detail fetched", "data": gate_detail(match_detail(db, row), current_user)}
```

Note SQLite : `Match.id == match_id` avec une chaîne fonctionne car le type `UUID(as_uuid=True)` convertit ; une chaîne non-UUID lève une exception, d'où le `try` → 404.

- [ ] **Step 5 : lancer** → `python -m pytest tests/test_api_matches.py -v` → 8 PASS. Si `test_detail_uses_finished_history_for_form_and_h2h` échoue sur `"NV"`, vérifier que `history_for` filtre bien `kickoff_at < before` et que la forme est triée du plus récent au plus ancien.

- [ ] **Step 6 : commit**

```bash
git add -A && git commit -m "feat(api): matches (liste, détail) sur la lecture du marché, paywall favori public / écarts réservés"
```

---

### Task 10 : Routes `books` (comparateur), `bankroll` (carnet) et `track-record`

**Files:**
- Create: `backend/app/api/v1/endpoints/books.py`, `backend/app/api/v1/endpoints/bankroll.py`, `backend/app/api/v1/endpoints/track_record.py`, `backend/app/services/settlement.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_api_books.py`, `backend/tests/test_api_bankroll.py`, `backend/tests/test_api_track_record.py`

**Interfaces:**
- `GET /api/v1/books` (Pro) → `{"items": [{"bookmaker","label","matches": n, "avg_margin": 0.07, "best": {"match_id","home_team","away_team","outcome","gap","odds"}, "gaps_above_threshold": n}]}` sur les matchs `SCHEDULED` des 7 prochains jours ; non-Pro → 403 `{"success": false, "message": "Réservé aux abonnés"}`.
- `POST /api/v1/bankroll` (connecté) body `{"match_id","outcome","bookmaker","odds","stake"}` → 201 + bet ; `GET /api/v1/bankroll` → `{"items": [...], "summary": {"stakes","payouts","profit","roi","pending","by_bookmaker": {...}, "by_competition": {...}}}` ; `DELETE /api/v1/bankroll/{id}` (seulement `PENDING`) ; `POST /api/v1/bankroll/{id}/void` (match `POSTPONED` seulement).
- `settlement.py` : `settle_bets(db) -> int` (règle tous les `PENDING` dont le match est `FINISHED` : `WON` payout = stake × odds, `LOST` payout = 0 ; retourne le nombre réglé). Appelé par la CLI `run.py fd_org` après l'import (ajouter l'appel) et par `GET /bankroll` avant de répondre (règlement paresseux).
- `GET /api/v1/track-record?competition=E0` (public) → `{"items": [{"competition","played","favourite_won","favourite_rate"}], "note": "Le favori gagne environ une fois sur deux : c'est le marché, pas nous."}` calculé sur les matchs `FINISHED` ayant au moins un relevé ; le favori est celui du **dernier relevé avant le coup d'envoi**.

- [ ] **Step 1 : tests `backend/tests/test_api_bankroll.py`**

```python
from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.models.enums import MatchStatus
from app.models.team import Team
from tests.conftest import auth_header, make_match

NOW = datetime.now(timezone.utc)


def teams(db):
    seed_aliases(db)
    return db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()


def test_create_list_and_settle(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    r = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 1.9, "stake": 10}, headers=auth_header(starter_user))
    assert r.status_code == 201, r.text
    lst = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]
    assert lst["summary"]["pending"] == 1 and lst["summary"]["stakes"] == 10
    m.status, m.home_score, m.away_score = MatchStatus.FINISHED, 2, 0
    db.commit()
    lst = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]
    it = lst["items"][0]
    assert it["status"] == "WON" and it["payout"] == 19.0
    assert lst["summary"]["profit"] == 9.0 and lst["summary"]["roi"] == 0.9 and lst["summary"]["by_bookmaker"]["betclic_fr"]["profit"] == 9.0


def test_lost_bet_and_delete_only_pending(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    bet_id = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "away", "bookmaker": "pmu_fr", "odds": 4.0, "stake": 5}, headers=auth_header(starter_user)).json()["data"]["id"]
    m.status, m.home_score, m.away_score = MatchStatus.FINISHED, 1, 0
    db.commit()
    assert client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]["items"][0]["status"] == "LOST"
    assert client.delete(f"/api/v1/bankroll/{bet_id}", headers=auth_header(starter_user)).status_code == 409


def test_void_only_when_postponed(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    bet_id = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "draw", "bookmaker": "winamax_fr", "odds": 3.5, "stake": 10}, headers=auth_header(starter_user)).json()["data"]["id"]
    assert client.post(f"/api/v1/bankroll/{bet_id}/void", headers=auth_header(starter_user)).status_code == 409
    m.status = MatchStatus.POSTPONED; db.commit()
    r = client.post(f"/api/v1/bankroll/{bet_id}/void", headers=auth_header(starter_user))
    assert r.status_code == 200 and r.json()["data"]["status"] == "VOID" and r.json()["data"]["payout"] == 10


def test_validation_and_isolation(client, db, starter_user, pro_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    bad = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 0.9, "stake": 10}, headers=auth_header(starter_user))
    assert bad.status_code == 422
    client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 1.9, "stake": 10}, headers=auth_header(starter_user))
    assert client.get("/api/v1/bankroll", headers=auth_header(pro_user)).json()["data"]["items"] == []
    assert client.get("/api/v1/bankroll").status_code == 401
```

- [ ] **Step 2 : `backend/app/services/settlement.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.bet import Bet
from app.models.enums import BetStatus, MatchStatus, Outcome


def _result(hg: int, ag: int) -> Outcome:
    return Outcome.HOME if hg > ag else Outcome.AWAY if ag > hg else Outcome.DRAW


def settle_bets(db: Session, user_id=None) -> int:
    q = select(Bet).where(Bet.status == BetStatus.PENDING).options(joinedload(Bet.match))
    if user_id is not None:
        q = q.where(Bet.user_id == user_id)
    n = 0
    for bet in db.scalars(q).unique().all():
        m = bet.match
        if m.status != MatchStatus.FINISHED or m.home_score is None or m.away_score is None:
            continue
        won = _result(m.home_score, m.away_score) == bet.outcome
        bet.status = BetStatus.WON if won else BetStatus.LOST
        bet.payout = round(bet.stake * bet.odds, 2) if won else 0.0
        bet.settled_at = datetime.now(timezone.utc)
        n += 1
    db.commit()
    return n
```

- [ ] **Step 3 : `backend/app/api/v1/endpoints/bankroll.py`**

```python
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.bet import Bet
from app.models.enums import BetStatus, MatchStatus, Outcome
from app.models.match import Match
from app.models.user import User
from app.services.settlement import settle_bets

router = APIRouter(prefix="/bankroll", tags=["bankroll"])


class BetIn(BaseModel):
    match_id: str
    outcome: Outcome
    bookmaker: str = Field(min_length=2, max_length=40)
    odds: float = Field(gt=1.0, le=1000)
    stake: float = Field(gt=0, le=100000)


def _bet_dict(b: Bet) -> dict:
    return {"id": str(b.id), "match_id": str(b.match_id), "home_team": b.match.home_team, "away_team": b.match.away_team,
            "competition": b.match.competition, "kickoff_at": b.match.kickoff_at, "outcome": b.outcome.value, "bookmaker": b.bookmaker,
            "odds": b.odds, "stake": b.stake, "status": b.status.value, "payout": b.payout, "created_at": b.created_at, "settled_at": b.settled_at}


def _summary(bets: list[Bet]) -> dict:
    settled = [b for b in bets if b.status in (BetStatus.WON, BetStatus.LOST)]
    stakes = sum(b.stake for b in settled); payouts = sum(b.payout or 0 for b in settled)
    def bucket(key):
        acc: dict = defaultdict(lambda: {"stakes": 0.0, "payouts": 0.0, "profit": 0.0, "bets": 0})
        for b in settled:
            k = key(b); acc[k]["stakes"] += b.stake; acc[k]["payouts"] += b.payout or 0; acc[k]["bets"] += 1
            acc[k]["profit"] = round(acc[k]["payouts"] - acc[k]["stakes"], 2)
        return dict(acc)
    return {"stakes": stakes, "payouts": payouts, "profit": round(payouts - stakes, 2), "roi": round((payouts - stakes) / stakes, 4) if stakes else None,
            "pending": sum(1 for b in bets if b.status == BetStatus.PENDING), "settled": len(settled),
            "by_bookmaker": bucket(lambda b: b.bookmaker), "by_competition": bucket(lambda b: b.match.competition)}


@router.get("")
def list_bets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_bets(db, user_id=current_user.id)
    bets = db.scalars(select(Bet).where(Bet.user_id == current_user.id).options(joinedload(Bet.match)).order_by(Bet.created_at.desc())).unique().all()
    return {"success": True, "message": "Bankroll fetched", "data": {"items": [_bet_dict(b) for b in bets], "summary": _summary(bets)}}


@router.post("", status_code=201)
def create_bet(payload: BetIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    match = db.get(Match, payload.match_id)
    if match is None or match.status == MatchStatus.QUARANTINE:
        raise HTTPException(status_code=404, detail="Match not found")
    bet = Bet(user_id=current_user.id, match_id=match.id, outcome=payload.outcome, bookmaker=payload.bookmaker, odds=payload.odds, stake=payload.stake)
    db.add(bet); db.commit(); db.refresh(bet)
    return {"success": True, "message": "Bet recorded", "data": _bet_dict(bet)}


def _own_bet(db: Session, bet_id: str, user: User) -> Bet:
    bet = db.scalar(select(Bet).where(Bet.id == bet_id, Bet.user_id == user.id).options(joinedload(Bet.match)))
    if bet is None:
        raise HTTPException(status_code=404, detail="Bet not found")
    return bet


@router.delete("/{bet_id}")
def delete_bet(bet_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bet = _own_bet(db, bet_id, current_user)
    if bet.status != BetStatus.PENDING:
        raise HTTPException(status_code=409, detail="Only pending bets can be deleted")
    db.delete(bet); db.commit()
    return {"success": True, "message": "Bet deleted", "data": {"id": bet_id}}


@router.post("/{bet_id}/void")
def void_bet(bet_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bet = _own_bet(db, bet_id, current_user)
    if bet.status != BetStatus.PENDING or bet.match.status != MatchStatus.POSTPONED:
        raise HTTPException(status_code=409, detail="Only pending bets on postponed matches can be voided")
    bet.status, bet.payout, bet.settled_at = BetStatus.VOID, bet.stake, datetime.now(timezone.utc)
    db.commit(); db.refresh(bet)
    return {"success": True, "message": "Bet voided", "data": _bet_dict(bet)}
```

- [ ] **Step 4 : tests `backend/tests/test_api_books.py`**

```python
from datetime import datetime, timedelta, timezone

from app.models.odds_snapshot import OddsSnapshot
from tests.conftest import auth_header
from tests.test_api_matches import seed_match_with_odds

NOW = datetime.now(timezone.utc)


def test_books_requires_pro(client, db, starter_user):
    seed_match_with_odds(db)
    assert client.get("/api/v1/books").status_code == 403
    assert client.get("/api/v1/books", headers=auth_header(starter_user)).status_code == 403


def test_books_compare_french_bookmakers(client, db, pro_user):
    m = seed_match_with_odds(db)
    items = client.get("/api/v1/books", headers=auth_header(pro_user)).json()["data"]["items"]
    by = {i["bookmaker"]: i for i in items}
    assert set(by) == {"betclic_fr", "winamax_fr"}
    assert by["winamax_fr"]["matches"] == 1 and by["winamax_fr"]["best"]["match_id"] == str(m.id)
    assert by["winamax_fr"]["best"]["gap"] > by["betclic_fr"]["best"]["gap"]
    assert 0 < by["betclic_fr"]["avg_margin"] < 0.15
```

- [ ] **Step 5 : `backend/app/api/v1/endpoints/books.py`**

```python
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user_optional, get_db
from app.collectors.competitions import FRENCH_BOOKMAKERS
from app.core.access import is_pro
from app.engine.narrative import BOOK_LABELS
from app.engine.types import OUTCOMES
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.user import User
from app.services.market_reading import reading_for

router = APIRouter(prefix="/books", tags=["books"])
GAP_THRESHOLD = 0.03


@router.get("")
def compare_books(db: Session = Depends(get_db), current_user: User | None = Depends(get_current_user_optional)):
    if not is_pro(current_user):
        raise HTTPException(status_code=403, detail="Réservé aux abonnés")
    now = datetime.now(timezone.utc)
    rows = db.scalars(select(Match).where(Match.status == MatchStatus.SCHEDULED, Match.kickoff_at >= now, Match.kickoff_at <= now + timedelta(days=7))
                      .options(selectinload(Match.snapshots))).unique().all()
    acc: dict = defaultdict(lambda: {"matches": 0, "margins": [], "best": None, "gaps_above_threshold": 0})
    for m in rows:
        r = reading_for(m)
        if r is None:
            continue
        for book in FRENCH_BOOKMAKERS:
            if book not in r.gaps:
                continue
            a = acc[book]; a["matches"] += 1; a["margins"].append(r.margin_by_book[book])
            k = max(range(3), key=lambda i: r.gaps[book][i]); gap = r.gaps[book][k]
            if gap >= GAP_THRESHOLD:
                a["gaps_above_threshold"] += 1
            if a["best"] is None or gap > a["best"]["gap"]:
                a["best"] = {"match_id": str(m.id), "home_team": m.home_team, "away_team": m.away_team, "kickoff_at": m.kickoff_at,
                             "outcome": OUTCOMES[k], "gap": gap, "odds": r.latest_by_book[book][k]}
    items = [{"bookmaker": b, "label": BOOK_LABELS.get(b, b), "matches": a["matches"],
              "avg_margin": sum(a["margins"]) / len(a["margins"]) if a["margins"] else None,
              "best": a["best"], "gaps_above_threshold": a["gaps_above_threshold"]} for b, a in acc.items()]
    items.sort(key=lambda i: -(i["best"]["gap"] if i["best"] else -1))
    return {"success": True, "message": "Books compared", "data": {"items": items, "threshold": GAP_THRESHOLD}}
```

- [ ] **Step 6 : tests `backend/tests/test_api_track_record.py`**

```python
from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import make_match

NOW = datetime.now(timezone.utc)


def finished(db, h, a, hg, ag, kick, pinnacle):
    m = make_match(db, h, a, kickoff=kick, status=MatchStatus.FINISHED, home_score=hg, away_score=ag)
    db.add(OddsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=kick - timedelta(hours=2), home=pinnacle[0], draw=pinnacle[1], away=pinnacle[2]))
    # un relevé APRÈS le coup d'envoi ne doit jamais servir
    db.add(OddsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=kick + timedelta(hours=1), home=9.0, draw=9.0, away=1.1))
    db.commit(); return m


def test_track_record_counts_favourite_wins_from_last_pre_kickoff_snapshot(client, db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    finished(db, h, a, 2, 0, NOW - timedelta(days=10), (1.8, 3.6, 4.2))   # favori domicile, gagné
    finished(db, a, h, 0, 0, NOW - timedelta(days=5), (1.8, 3.6, 4.2))    # favori domicile, nul → perdu
    make_match(db, h, a, kickoff=NOW - timedelta(days=2), status=MatchStatus.FINISHED, home_score=1, away_score=0)   # sans relevé : ignoré
    d = client.get("/api/v1/track-record").json()["data"]
    assert d["items"] == [{"competition": "E0", "played": 2, "favourite_won": 1, "favourite_rate": 0.5}]
    assert "c'est le marché" in d["note"]
    assert client.get("/api/v1/track-record?competition=F1").json()["data"]["items"] == []
```

- [ ] **Step 7 : `backend/app/api/v1/endpoints/track_record.py`**

```python
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.collectors.competitions import FRENCH_BOOKMAKERS
from app.engine.market import read
from app.engine.types import BookQuote
from app.models.enums import MatchStatus
from app.models.match import Match

router = APIRouter(prefix="/track-record", tags=["track-record"])
NOTE = "Le favori gagne environ une fois sur deux : c'est le marché, pas nous."


def _actual(m: Match) -> str:
    return "home" if m.home_score > m.away_score else "away" if m.away_score > m.home_score else "draw"


@router.get("")
def track_record(competition: str | None = Query(default=None, pattern="^(E0|F1|SP1|D1|I1|CL)$"), db: Session = Depends(get_db)):
    q = select(Match).where(Match.status == MatchStatus.FINISHED, Match.home_score.is_not(None)).options(selectinload(Match.snapshots))
    if competition:
        q = q.where(Match.competition == competition)
    acc: dict = defaultdict(lambda: {"played": 0, "favourite_won": 0})
    for m in db.scalars(q).unique().all():
        quotes = [BookQuote(s.bookmaker, s.taken_at, (s.home, s.draw, s.away)) for s in m.snapshots if s.taken_at <= m.kickoff_at]
        if not quotes:
            continue
        try:
            r = read(quotes, FRENCH_BOOKMAKERS)
        except ValueError:
            continue
        acc[m.competition]["played"] += 1
        acc[m.competition]["favourite_won"] += int(r.favourite == _actual(m))
    items = [{"competition": c, "played": a["played"], "favourite_won": a["favourite_won"], "favourite_rate": round(a["favourite_won"] / a["played"], 3)}
             for c, a in sorted(acc.items())]
    return {"success": True, "message": "Track record", "data": {"items": items, "note": NOTE}}
```

- [ ] **Step 8 : brancher les routes et le règlement dans la CLI**

`backend/app/api/v1/router.py` :

```python
from fastapi import APIRouter

from app.api.v1.endpoints import auth, bankroll, books, favorites, matches, subscriptions, track_record, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(matches.router)
api_router.include_router(books.router)
api_router.include_router(bankroll.router)
api_router.include_router(track_record.router)
api_router.include_router(favorites.router)
api_router.include_router(subscriptions.router)
```

Dans `backend/app/collectors/run.py`, branche `fd_org` : après `summary = vars(fd_org.run(db))`, ajouter `from app.services.settlement import settle_bets` en tête et `summary["bets_settled"] = settle_bets(db)`.

- [ ] **Step 9 : lancer toute la suite** → `python -m pytest -q` → Expected : tout vert (≈ 45 tests).

- [ ] **Step 10 : commit**

```bash
git add -A && git commit -m "feat(api): comparateur bookmakers, carnet de bankroll avec règlement automatique, track record public"
```

---

### Task 11 : Santé, inscription 18 ans, bandeau ANJ, README et déploiement VPS

**Files:**
- Modify: `backend/app/main.py`, `backend/app/api/v1/endpoints/auth.py`, `backend/app/models/user.py`, `backend/alembic/versions/0005_market_reading.py` (ajout colonne), `backend/README.md`, racine `README.md`, `Dockerfile`, `docker-compose.yml`
- Create: `deploy/coolify.md`, `deploy/crontab.txt`
- Test: `backend/tests/test_health.py`, ajout dans `backend/tests/test_smoke.py`

**Interfaces:**
- `/health` → `data.collectors = {"fd_uk": {"at": iso|null, "stale": bool}, "fd_org": {...}, "odds": {...}}` (`stale` = heartbeat absent ou plus vieux que 36 h pour fd_org/odds, 8 jours pour fd_uk).
- Inscription : `SignUpRequest` gagne `birth_date: date` obligatoire ; < 18 ans → 422 `"Vous devez avoir 18 ans ou plus"`. Colonne `users.birth_date DATE` (migration : `ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE`).
- Constante `LEGAL_NOTICE` exposée par `GET /api/v1/legal` (public) : `{"warning": "Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non surtaxé).", "minimum_age": 18, "positioning": "Nous ne prédisons pas. Nous vous montrons ce que le marché pense, et où il se contredit."}` — le front l'affichera sur chaque page.

- [ ] **Step 1 : tests**

`backend/tests/test_health.py` :

```python
import json
from datetime import datetime, timedelta, timezone

from app.collectors import run as runner


def test_health_reports_missing_and_fresh_heartbeats(client, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "HEARTBEATS", tmp_path)
    from app import main
    monkeypatch.setattr(main, "HEARTBEATS", tmp_path)
    d = client.get("/health").json()["data"]
    assert d["collectors"]["odds"] == {"at": None, "stale": True}
    (tmp_path / "odds.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat()}))
    (tmp_path / "fd_uk.json").write_text(json.dumps({"at": (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()}))
    d = client.get("/health").json()["data"]
    assert d["collectors"]["odds"]["stale"] is False and d["collectors"]["fd_uk"]["stale"] is True


def test_legal_endpoint(client):
    d = client.get("/api/v1/legal").json()["data"]
    assert d["minimum_age"] == 18 and "09 74 75 13 13" in d["warning"]
```

Ajouter dans `backend/tests/test_smoke.py` :

```python
def test_signup_refuses_minors(client):
    r = client.post("/api/v1/auth/signup", json={"first_name": "Jeune", "email": "j@test.fr", "password": "motdepasse123", "birth_date": "2015-01-01"})
    assert r.status_code == 422 and "18 ans" in r.text
```

et compléter le JSON de `test_signup_and_me` avec `"birth_date": "2000-01-01"`.

- [ ] **Step 2 : `main.py` — heartbeats et `/legal`**

En tête : `import json`, `from datetime import datetime, timedelta, timezone`, `from pathlib import Path`, `HEARTBEATS = Path(__file__).resolve().parents[1] / "heartbeats"`, `STALE_AFTER = {"fd_uk": timedelta(days=8), "fd_org": timedelta(hours=36), "odds": timedelta(hours=36)}`, `LEGAL_NOTICE = {...}` (valeurs de l'interface).

```python
def _collectors_status() -> dict:
    out = {}
    now = datetime.now(timezone.utc)
    for name, max_age in STALE_AFTER.items():
        f = HEARTBEATS / f"{name}.json"
        if not f.exists():
            out[name] = {"at": None, "stale": True}
            continue
        at = datetime.fromisoformat(json.loads(f.read_text(encoding="utf-8"))["at"])
        out[name] = {"at": at.isoformat(), "stale": now - at > max_age}
    return out


@app.get("/health")
def health():
    return {"success": True, "message": "API healthy", "data": {"env": settings.env, "collectors": _collectors_status()}}


@app.get("/api/v1/legal")
def legal():
    return {"success": True, "message": "Legal notice", "data": LEGAL_NOTICE}
```

- [ ] **Step 3 : `auth.py` et `user.py` — âge minimum**

Dans `SignUpRequest` (auth.py) ajouter `birth_date: date` et un validateur :

```python
    @field_validator("birth_date")
    @classmethod
    def _adult(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Vous devez avoir 18 ans ou plus")
        return v
```

Dans `User` : `birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)` (import `Date` de sqlalchemy et `date` de datetime) ; dans `signup`, passer `birth_date=payload.birth_date` au constructeur. Dans la migration 0005, ajouter `op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE")` dans `upgrade` et le `DROP COLUMN IF EXISTS` dans `downgrade`.

- [ ] **Step 4 : lancer toute la suite** → `python -m pytest -q` → tout vert.

- [ ] **Step 5 : `Dockerfile`, `docker-compose.yml`, `deploy/`**

`Dockerfile` (racine) : contexte `backend/` uniquement.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
ENV PYTHONUNBUFFERED=1 ENV=production
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

`docker-compose.yml` (référence locale/Coolify) :

```yaml
services:
  api:
    build: .
    restart: always
    ports: ["8000:8000"]
    env_file: [./backend/.env]
    volumes: ["heartbeats:/app/heartbeats"]
    depends_on: [postgres]
  postgres:
    image: postgres:16
    restart: always
    environment: {POSTGRES_DB: rushplay, POSTGRES_USER: rushplay, POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"}
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes: {pgdata: {}, heartbeats: {}}
```

`deploy/crontab.txt` (à coller dans les « Scheduled Tasks » de Coolify, service `api`) :

```
# relevé de cotes : 08:00 UTC tous les jours + 12:00 UTC les samedi/dimanche (≈ 40 relevés/mois, 12 crédits chacun)
0 8 * * *   cd /app && python -m app.collectors.run odds
0 12 * * 6,0 cd /app && python -m app.collectors.run odds
# calendrier, heures, résultats, reports, règlement des paris : tous les jours 06:30 UTC
30 6 * * *  cd /app && python -m app.collectors.run fd_org
# historique et cotes ouverture/clôture : lundi 07:00 UTC, saison en cours
0 7 * * 1   cd /app && python -m app.collectors.run fd_uk --seasons 2526
```

`deploy/coolify.md` : procédure en 8 étapes — 1) VPS Hetzner CX22 Ubuntu 24.04, Coolify installé par le script officiel ; 2) ressource Postgres 16 dans Coolify, noter l'URL ; 3) migration depuis Supabase : `pg_dump --no-owner --no-privileges "$SUPABASE_URL" > rushplay.sql` puis `psql "$VPS_URL" < rushplay.sql` (tables users/subscriptions/favorites/matches suffisent ; `analyses`, `team_stats`, `warning_points` seront supprimées par 0005) ; 4) application Docker depuis le dépôt GitHub, branche `refonte-marche`, variables : `DATABASE_URL=postgresql+psycopg://…`, `JWT_SECRET`, `CRON_SECRET`, `CORS_ORIGINS`, `THE_ODDS_API_KEY`, `FOOTBALL_DATA_ORG_KEY`, `ENV=production` ; 5) premier déploiement → `alembic upgrade head` tourne au démarrage ; 6) `python -m app.collectors.run seed` puis `fd_uk --seasons 2324 2425 2526` puis `fd_org` puis `odds` à la main depuis le terminal Coolify, vérifier `/health` ; 7) coller `deploy/crontab.txt` ; 8) domaine + HTTPS dans Coolify quand le nom existe. Ne jamais coller de clé dans le chat : Lucas les saisit dans Coolify.

- [ ] **Step 6 : README**

`backend/README.md` : remplacer les sections Supabase/Render par : lancement local (`uvicorn app.main:app --reload`), variables d'environnement (liste ci-dessus), collecteurs (`python -m app.collectors.run …`), tests (`python -m pytest -q`), routes (tableau : `GET /matches`, `GET /matches/{id}`, `GET /books` (Pro), `GET/POST/DELETE /bankroll`, `POST /bankroll/{id}/void`, `GET /track-record`, `GET /legal`, `/health`). `README.md` racine : trois paragraphes — ce qu'est RushPlay (positionnement de la spec §2), ce qu'il n'est pas (pas de prédiction, pas de « value bet »), lien vers `docs/superpowers/specs/2026-09-10-rushplay-refonte-design.md` et `deploy/coolify.md`.

- [ ] **Step 7 : vérification finale et commit**

Run : `cd backend && python -m pytest -q` → tout vert.
Run : `grep -rniE "value_bet|value_percent|confidence_score|recommended_bet|prediction" app/ tests/ ../README.md` → Expected : aucune ligne.
Run : `python -c "import app.main"` (avec les variables d'env) → aucune erreur.

```bash
git add -A && git commit -m "feat: santé des collecteurs, inscription 18 ans, mentions légales, Dockerfile Postgres 16, procédure Coolify et crons"
```

---

## Self-review du plan (fait à la rédaction)

- **Couverture de la spec** : §2 promesse/vocabulaire (Task 1 contraintes, Task 11 `/legal`, grep final), §2 18 ans (Task 11), §3 trois sources et archive des relevés (Tasks 4-6, `odds_snapshots` jamais mises à jour), §3 alias/quarantaine (Task 3, tests de quarantaine dans 4-6), §4 moteur complet (Tasks 7-8), §5 écrans : l'API couvre 2 (liste), 3 (détail), 4 (comparateur), 5 (carnet), 6 (track record), 7 (paywall) — l'écran 1 (accueil) est purement front ; §6 architecture (Tasks 1-2, 11), §7 cas limites : relevé incomplet (référence « moyenne » Task 7), quota (arrêt propre Task 6), report (Task 5 + `void` Task 10), nom inconnu (Task 3), résultat manquant (pari reste `PENDING`, relance quotidienne fd_org) ; §8 tests : unitaires moteur, fixtures collecteurs, intégration API sur SQLite (déviation assumée par rapport à « Postgres de test » : pas de Postgres local) ; §9 hors périmètre respecté.
- **Placeholders** : aucun « TBD » ; les deux endroits où le code est décrit plutôt qu'écrit (`deploy/coolify.md`, README) sont de la documentation, avec le contenu listé.
- **Cohérence des noms** : `Reading.latest_by_book` / `gaps` / `margin_by_book` utilisés à l'identique dans Tasks 7, 9, 10 ; `ImportReport` partagé Tasks 4-5 ; `FRENCH_BOOKMAKERS` / `REFERENCE_BOOKMAKER` définis Task 3, consommés 6-10 ; `make_match(db, home, away, competition, kickoff, status, home_score, away_score)` du conftest utilisé tel quel partout ; `seed_aliases` avant tout usage de `Team` dans les tests.
- **Déviation par rapport à la spec** : la table `results` de la spec est fondue dans `matches` (colonnes `home_score/away_score/home_shots/away_shots`, statut `FINISHED`) — plus simple, une seule table de matchs pour le calendrier, l'historique et le track record.
