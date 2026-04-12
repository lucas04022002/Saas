from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models.analysis import Analysis
from app.models.match import Match
from app.models.team_stats import TeamStats
from app.models.enums import TeamType

router = APIRouter(prefix="/signal", tags=["signal"])


@router.get("/{match_id}")
def get_signal(match_id: UUID, db: Session = Depends(get_db)):
    match = db.scalar(
        select(Match)
        .options(
            joinedload(Match.analysis).joinedload(Analysis.warning_points),
            joinedload(Match.team_stats),
        )
        .where(Match.id == match_id)
    )

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    analysis = match.analysis
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis for this match")

    home_stats = next((s for s in match.team_stats if s.team_type == TeamType.HOME), None)
    away_stats = next((s for s in match.team_stats if s.team_type == TeamType.AWAY), None)

    return {
        "success": True,
        "data": {
            "match": {
                "id": str(match.id),
                "home_team": match.home_team,
                "away_team": match.away_team,
                "league": match.league,
                "country": match.country,
                "kickoff_at": match.kickoff_at.isoformat(),
                "status": match.status.value,
            },
            "analysis": {
                "confidence_score": analysis.confidence_score,
                "recommended_bet": analysis.recommended_bet,
                "bookmaker_odds": analysis.bookmaker_odds,
                "value_percent": analysis.value_percent,
                "risk_level": analysis.risk_level.value,
                "ai_explanation": analysis.ai_explanation,
                "updated_at": analysis.updated_at.isoformat(),
            },
            "warning_points": [wp.label for wp in analysis.warning_points],
            "home_form": home_stats.recent_form if home_stats else None,
            "away_form": away_stats.recent_form if away_stats else None,
        },
    }
