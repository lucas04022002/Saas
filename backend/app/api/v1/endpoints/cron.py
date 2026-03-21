import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.analysis import Analysis
from app.models.match import Match
from app.services.analysis_runner import run_bulk_analyses

router = APIRouter(prefix="/cron", tags=["cron"])


def _verify_cron_key(x_cron_key: str | None = Header(default=None, alias="X-CRON-KEY")) -> None:
    if not settings.cron_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="CRON_SECRET not configured")
    if not x_cron_key or not hmac.compare_digest(x_cron_key, settings.cron_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron key")


@router.post("/daily-run")
def daily_run(
    _: None = Depends(_verify_cron_key),
    limit: int | None = Query(default=None, ge=1, le=500),
    league: str | None = Query(default=None),
    only_missing: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    query = select(Match).order_by(Match.kickoff_at.asc())

    if league:
        query = query.where(Match.league.ilike(f"%{league}%"))
    if only_missing:
        query = query.outerjoin(Analysis).where(Analysis.id.is_(None))
    if limit:
        query = query.limit(limit)

    matches = db.scalars(query).all()
    if not matches:
        return {
            "success": True,
            "message": "No matches found for cron run",
            "data": {"processed": 0, "created": 0, "updated": 0, "failed": 0, "errors": []},
        }

    summary = run_bulk_analyses(db, matches)
    return {"success": True, "message": "Daily cron run completed", "data": summary}
