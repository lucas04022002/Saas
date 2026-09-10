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
