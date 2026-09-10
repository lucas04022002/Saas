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


def match_detail(db: Session, match: Match, public: bool = False) -> dict:
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
    out["analysis"] = describe(MatchContext(match.home_team, match.away_team, r, hf, af, h2h, best_gap(r)), public=public)
    return out
