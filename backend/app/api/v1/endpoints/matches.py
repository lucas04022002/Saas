from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models.analysis import Analysis
from app.models.enums import MatchStatus
from app.models.match import Match

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("")
def list_matches(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    league: str | None = None,
    risk_level: str | None = None,
    min_confidence: float | None = Query(default=None, ge=0, le=100),
    recommended_bet: str | None = None,
    match_date: date | None = Query(default=None, alias="date"),
    status: str | None = Query(default=None, pattern="^(SCHEDULED|LIVE|FINISHED)$"),
    sort_by: str = Query(default="kickoff_at", pattern="^(kickoff_at|confidence_score|value_percent)$"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    query = select(Match).outerjoin(Analysis).options(joinedload(Match.analysis))

    if league:
        query = query.where(Match.league.ilike(f"%{league}%"))
    if risk_level:
        query = query.where(Analysis.risk_level == risk_level)
    if min_confidence is not None:
        query = query.where(Analysis.confidence_score >= min_confidence)
    if recommended_bet:
        query = query.where(Analysis.recommended_bet.ilike(f"%{recommended_bet}%"))
    if match_date:
        start_dt = datetime.combine(match_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(match_date, datetime.max.time(), tzinfo=timezone.utc)
        query = query.where(Match.kickoff_at >= start_dt, Match.kickoff_at <= end_dt)
    if status:
        query = query.where(Match.status == MatchStatus(status))

    total = db.scalar(select(func.count()).select_from(query.subquery()))

    sort_map = {
        "kickoff_at": Match.kickoff_at,
        "confidence_score": Analysis.confidence_score,
        "value_percent": Analysis.value_percent,
    }
    sort_column = sort_map[sort_by]
    sort_expr = desc(sort_column) if order == "desc" else asc(sort_column)

    rows = db.scalars(query.order_by(sort_expr).offset((page - 1) * limit).limit(limit)).unique().all()

    data = []
    for row in rows:
        analysis = row.analysis
        data.append(
            {
                "id": str(row.id),
                "home_team": row.home_team,
                "away_team": row.away_team,
                "league": row.league,
                "country": row.country,
                "kickoff_at": row.kickoff_at,
                "status": row.status.value,
                "last_analyzed_at": row.last_analyzed_at,
                "confidence_score": analysis.confidence_score if analysis else None,
                "recommended_bet": analysis.recommended_bet if analysis else None,
                "bookmaker_odds": analysis.bookmaker_odds if analysis else None,
                "value_percent": analysis.value_percent if analysis else None,
                "risk_level": analysis.risk_level.value if analysis else None,
            }
        )

    return {
        "success": True,
        "message": "Matches fetched successfully",
        "data": {"items": data, "pagination": {"page": page, "limit": limit, "total": total}},
    }


@router.get("/{match_id}")
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    row = db.scalar(
        select(Match)
        .where(Match.id == match_id)
        .options(
            joinedload(Match.analysis).joinedload(Analysis.warning_points),
            joinedload(Match.team_stats),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Match not found")

    analysis = None
    if row.analysis:
        analysis = {
            "confidence_score": row.analysis.confidence_score,
            "recommended_bet": row.analysis.recommended_bet,
            "bookmaker_odds": row.analysis.bookmaker_odds,
            "value_percent": row.analysis.value_percent,
            "risk_level": row.analysis.risk_level.value,
            "ai_explanation": row.analysis.ai_explanation,
            "warning_points": [wp.label for wp in row.analysis.warning_points],
        }

    return {
        "success": True,
        "message": "Match detail fetched successfully",
        "data": {
            "id": str(row.id),
            "home_team": row.home_team,
            "away_team": row.away_team,
            "league": row.league,
            "country": row.country,
            "kickoff_at": row.kickoff_at,
            "status": row.status.value,
            "last_analyzed_at": row.last_analyzed_at,
            "analysis": analysis,
            "team_stats": [
                {
                    "team_type": ts.team_type.value,
                    "recent_form": ts.recent_form,
                    "goals_scored": ts.goals_scored,
                    "goals_conceded": ts.goals_conceded,
                    "xg": ts.xg,
                    "xga": ts.xga,
                    "possession_avg": ts.possession_avg,
                    "shots_on_target_avg": ts.shots_on_target_avg,
                    "clean_sheets": ts.clean_sheets,
                }
                for ts in row.team_stats
            ],
        },
    }
