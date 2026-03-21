from datetime import datetime

from pydantic import BaseModel


class MatchCard(BaseModel):
    id: str
    home_team: str
    away_team: str
    league: str
    country: str
    kickoff_at: datetime
    status: str
    confidence_score: float | None = None
    recommended_bet: str | None = None
    bookmaker_odds: float | None = None
    value_percent: float | None = None
    risk_level: str | None = None


class TeamStatsOut(BaseModel):
    team_type: str
    recent_form: str
    goals_scored: int
    goals_conceded: int
    xg: float
    xga: float
    possession_avg: float
    shots_on_target_avg: float
    clean_sheets: int


class AnalysisOut(BaseModel):
    confidence_score: float
    recommended_bet: str
    bookmaker_odds: float
    value_percent: float
    risk_level: str
    ai_explanation: str
    warning_points: list[str]


class MatchDetail(BaseModel):
    id: str
    home_team: str
    away_team: str
    league: str
    country: str
    kickoff_at: datetime
    status: str
    analysis: AnalysisOut | None = None
    team_stats: list[TeamStatsOut] = []
