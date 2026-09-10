"""Analyse textuelle par gabarits : 3 à 4 phrases, déterministes, à partir des chiffres seulement."""
from dataclasses import dataclass

from app.engine.context import Form, PastMatch
from app.engine.types import Reading

BOOK_LABELS = {"betclic_fr": "Betclic", "winamax_fr": "Winamax", "unibet_fr": "Unibet", "pmu_fr": "PMU", "netbet_fr": "NetBet", "pinnacle": "Pinnacle",
               "fd_uk_pinnacle": "Pinnacle (archive)", "fd_uk_avg": "Marché (archive)"}
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
        if f.wins == 0:
            return "aucune victoire"
        return NUMBERS.get(f.wins, str(f.wins)) + (" victoire" if f.wins == 1 else " victoires")

    if hf.played and af.played:
        away_wins_text = "n'en compte aucune" if af.wins == 0 else f"sur {NUMBERS.get(af.wins, str(af.wins))}"
        return f"{ctx.home} reste sur {wins(hf)} lors des {NUMBERS[hf.played]} derniers matchs ; {ctx.away} {away_wins_text}."
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


def describe(ctx: MatchContext, public: bool = False) -> str:
    parts = [
        _favourite_sentence(ctx),
        None if public else _gap_sentence(ctx),
        None if public else _movement_sentence(ctx),
        _form_sentence(ctx),
        _h2h_sentence(ctx),
    ]
    return " ".join(p for p in parts if p)
