import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, get_db
from app.core.config import settings
from app.core.security import decode_access_token
from app.models.analysis import Analysis
from app.models.enums import UserRole
from app.models.match import Match
from app.models.user import User
from app.services.analysis_runner import run_bulk_analyses, upsert_analysis_for_match

router = APIRouter(prefix="/analyses", tags=["analyses"])
limiter = Limiter(key_func=get_remote_address)


def _is_valid_cron_key(x_cron_key: str | None) -> bool:
    if not x_cron_key or not settings.cron_secret:
        return False
    return hmac.compare_digest(x_cron_key, settings.cron_secret)


@router.get("")
def list_analyses(db: Session = Depends(get_db)):
    rows = db.execute(select(Analysis, Match).join(Match, Match.id == Analysis.match_id)).all()
    data = [
        {
            "match_id": str(analysis.match_id),
            "home_team": match.home_team,
            "away_team": match.away_team,
            "confidence_score": analysis.confidence_score,
            "recommended_bet": analysis.recommended_bet,
            "bookmaker_odds": analysis.bookmaker_odds,
            "value_percent": analysis.value_percent,
            "risk_level": analysis.risk_level.value,
            "ai_explanation": analysis.ai_explanation,
            "created_at": analysis.created_at,
        }
        for analysis, match in rows
    ]
    return {"success": True, "message": "Analyses fetched successfully", "data": data}


@router.get("/{match_id}")
def get_analysis(match_id: str, db: Session = Depends(get_db)):
    row = db.scalar(select(Analysis).where(Analysis.match_id == match_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return {
        "success": True,
        "message": "Analysis fetched successfully",
        "data": {
            "match_id": str(row.match_id),
            "confidence_score": row.confidence_score,
            "recommended_bet": row.recommended_bet,
            "bookmaker_odds": row.bookmaker_odds,
            "value_percent": row.value_percent,
            "risk_level": row.risk_level.value,
            "ai_explanation": row.ai_explanation,
            "warning_points": [w.label for w in row.warning_points],
        },
    }


@router.post("/{match_id}/run")
@limiter.limit("30/minute")
def run_analysis(request: Request, match_id: str, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    analysis, warning_labels, created = upsert_analysis_for_match(db, match)
    db.commit()
    db.refresh(analysis)

    return {
        "success": True,
        "message": "Analysis created successfully" if created else "Analysis updated successfully",
        "data": {
            "match_id": str(match.id),
            "home_team": match.home_team,
            "away_team": match.away_team,
            "confidence_score": analysis.confidence_score,
            "recommended_bet": analysis.recommended_bet,
            "bookmaker_odds": analysis.bookmaker_odds,
            "value_percent": analysis.value_percent,
            "risk_level": analysis.risk_level.value,
            "ai_explanation": analysis.ai_explanation,
            "warning_points": warning_labels,
        },
    }


@router.post("/run-all")
@limiter.limit("5/hour")
def run_all_analyses(
    request: Request,
    limit: int | None = Query(default=None, ge=1, le=500),
    league: str | None = Query(default=None),
    only_missing: bool = Query(default=False),
    x_cron_key: str | None = Header(default=None, alias="X-CRON-KEY"),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if not _is_valid_cron_key(x_cron_key):
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing access token")
        try:
            user_id = decode_access_token(credentials.credentials)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

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
            "message": "No matches found for analysis run",
            "data": {"processed": 0, "created": 0, "updated": 0, "failed": 0, "errors": []},
        }
    summary = run_bulk_analyses(db, matches)
    return {
        "success": True,
        "message": "Bulk analysis run completed",
        "data": summary,
    }
