import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user_optional, get_db
from app.core.access import gate_detail, gate_list, is_pro
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
        match_uuid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match not found")
    row = db.scalar(select(Match).where(Match.id == match_uuid).options(selectinload(Match.snapshots)))
    if row is None or row.status == MatchStatus.QUARANTINE:
        raise HTTPException(status_code=404, detail="Match not found")
    detail = match_detail(db, row, public=not is_pro(current_user))
    return {"success": True, "message": "Match detail fetched", "data": gate_detail(detail, current_user)}
