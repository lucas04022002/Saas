from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user_optional, get_db
from app.collectors.competitions import FRENCH_BOOKMAKERS
from app.core.access import is_pro
from app.core.time import to_utc_iso
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
                a["best"] = {"match_id": str(m.id), "home_team": m.home_team, "away_team": m.away_team, "kickoff_at": to_utc_iso(m.kickoff_at),
                             "outcome": OUTCOMES[k], "gap": gap, "odds": r.latest_by_book[book][k]}
    items = [{"bookmaker": b, "label": BOOK_LABELS.get(b, b), "matches": a["matches"],
              "avg_margin": sum(a["margins"]) / len(a["margins"]) if a["margins"] else None,
              "best": a["best"], "gaps_above_threshold": a["gaps_above_threshold"]} for b, a in acc.items()]
    items.sort(key=lambda i: -(i["best"]["gap"] if i["best"] else -1))
    return {"success": True, "message": "Books compared", "data": {"items": items, "threshold": GAP_THRESHOLD}}
