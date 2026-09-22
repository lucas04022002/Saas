import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.collectors.competitions import COMPETITION_PATTERN, FRENCH_BOOKMAKERS
from app.engine.market import read
from app.engine.types import BookQuote
from app.models.enums import MatchStatus
from app.models.match import Match
from app.services.market_reading import latest_totals_snapshot, score_for

router = APIRouter(prefix="/track-record", tags=["track-record"])
NOTE = "Le favori gagne environ une fois sur deux : c'est le marché, pas nous."
SCORE_NOTE = "Le marché touche le score exact environ une fois sur neuf."


def _actual(m: Match) -> str:
    return "home" if m.home_score > m.away_score else "away" if m.away_score > m.home_score else "draw"


def _outcome(i: int, j: int) -> str:
    return "home" if i > j else "away" if j > i else "draw"


#: Le résultat ne change qu'à l'arrivée des résultats, une fois par jour : une heure de cache suffit.
#: Sans cache, la route recalculait la grille de Poisson de tous les matchs terminés à chaque requête
#: (13,9 s en production sur 5 357 matchs, publique, non bornée — audit du 22/09/2026). Les collecteurs
#: tournent dans un autre processus : l'invalidation ne peut être que temporelle.
TTL_SECONDES = 3600
_CACHE: dict[str | None, tuple[float, dict]] = {}
_maintenant = time.monotonic


def vider_le_cache() -> None:
    _CACHE.clear()


@router.get("")
def track_record(competition: str | None = Query(default=None, pattern=COMPETITION_PATTERN), db: Session = Depends(get_db)):
    entree = _CACHE.get(competition)
    if entree is not None and _maintenant() - entree[0] < TTL_SECONDES:
        data = entree[1]
    else:
        data = compute_track_record(db, competition)
        _CACHE[competition] = (_maintenant(), data)
    return {"success": True, "message": "Track record", "data": data}


def compute_track_record(db: Session, competition: str | None) -> dict:
    q = select(Match).where(Match.status == MatchStatus.FINISHED, Match.home_score.is_not(None)).options(
        selectinload(Match.snapshots), selectinload(Match.totals))
    if competition:
        q = q.where(Match.competition == competition)
    acc: dict = defaultdict(lambda: {"played": 0, "favourite_won": 0})
    n_scored = exact = winner_from_score = 0
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
        # relevé de clôture (avant coup d'envoi), comme pour la lecture 1N2 ci-dessus
        totals_snapshot = latest_totals_snapshot(m.totals, before=m.kickoff_at)
        d = score_for(m.competition, r, totals_snapshot)
        if d is None:
            continue
        i, j = (int(x) for x in d.top.split("-"))
        n_scored += 1
        exact += int((i, j) == (m.home_score, m.away_score))
        winner_from_score += int(_outcome(i, j) == _actual(m))
    items = [{"competition": c, "played": a["played"], "favourite_won": a["favourite_won"], "favourite_rate": round(a["favourite_won"] / a["played"], 3)}
             for c, a in sorted(acc.items())]
    data = {
        "items": items, "note": NOTE,
        "n_scored": n_scored,
        "exact_score_rate": round(exact / n_scored, 3) if n_scored else None,
        "winner_rate_from_score": round(winner_from_score / n_scored, 3) if n_scored else None,
        "score_note": SCORE_NOTE,
    }
    return data
