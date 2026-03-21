from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.analysis import Analysis
from app.models.match import Match

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _serialize(match: Match, analysis: Analysis) -> dict:
    return {
        "match_id": str(match.id),
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "kickoff_at": match.kickoff_at,
        "confidence_score": analysis.confidence_score,
        "recommended_bet": analysis.recommended_bet,
        "bookmaker_odds": analysis.bookmaker_odds,
        "value_percent": analysis.value_percent,
        "risk_level": analysis.risk_level.value,
        "last_analyzed_at": match.last_analyzed_at,
        "short_ai_explanation": analysis.ai_explanation[:140],
    }


@router.get("")
def list_opportunities(
    min_value: float = Query(default=0.0),
    min_confidence: float = Query(default=0.0),
    recent_hours: int | None = Query(default=72, ge=1, le=720),
    db: Session = Depends(get_db),
):
    query = (
        select(Match, Analysis)
        .join(Analysis, Analysis.match_id == Match.id)
        .where(Analysis.value_percent >= min_value)
        .where(Analysis.confidence_score >= min_confidence)
        .order_by(desc(Analysis.value_percent), desc(Analysis.confidence_score))
    )

    if recent_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
        query = query.where(Match.last_analyzed_at.is_not(None)).where(Match.last_analyzed_at >= cutoff)

    rows = db.execute(query).all()

    return {
        "success": True,
        "message": "Opportunities fetched successfully",
        "data": [_serialize(match, analysis) for match, analysis in rows],
    }


@router.get("/top")
def top_opportunities(
    limit: int = Query(default=5, ge=1, le=20),
    recent_hours: int | None = Query(default=72, ge=1, le=720),
    db: Session = Depends(get_db),
):
    query = (
        select(Match, Analysis)
        .join(Analysis, Analysis.match_id == Match.id)
        .order_by(desc(Analysis.confidence_score), desc(Analysis.value_percent))
        .limit(limit)
    )

    if recent_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
        query = query.where(Match.last_analyzed_at.is_not(None)).where(Match.last_analyzed_at >= cutoff)

    rows = db.execute(query).all()

    return {
        "success": True,
        "message": "Top opportunities fetched successfully",
        "data": [_serialize(match, analysis) for match, analysis in rows],
    }
