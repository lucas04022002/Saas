import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger("rushplay.cron")

from app.api.deps import get_db
from app.core.config import settings
from app.models.analysis import Analysis
from app.models.match import Match
from app.services.analysis_runner import run_bulk_analyses
from app.services.match_importer import import_upcoming_matches
from app.services.odds_fetcher import fetch_upcoming_odds

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

    try:
        matches = db.scalars(query).all()
    except Exception as exc:
        log.error("Failed to fetch matches for cron: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Database error: {exc}")

    if not matches:
        return {
            "success": True,
            "message": "No matches found for cron run",
            "data": {"processed": 0, "created": 0, "updated": 0, "failed": 0, "errors": []},
        }

    odds_map: dict | None = None
    if settings.api_football_key:
        try:
            odds_map = fetch_upcoming_odds(settings.api_football_key)
            log.info("Fetched odds for %d fixtures", len(odds_map))
        except Exception as exc:
            log.warning("Odds fetch failed, continuing without real odds: %s", exc)

    try:
        summary = run_bulk_analyses(db, matches, odds_map=odds_map)
    except Exception as exc:
        log.error("Unhandled error in run_bulk_analyses: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis runner error: {exc}")

    return {"success": True, "message": "Daily cron run completed", "data": summary}


@router.post("/import-matches")
def import_matches(
    _: None = Depends(_verify_cron_key),
    next_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    if not settings.api_football_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_FOOTBALL_KEY not configured on this server",
        )

    summary = import_upcoming_matches(db, settings.api_football_key, next_days=next_days)
    return {"success": True, "message": "Match import completed", "data": summary}
