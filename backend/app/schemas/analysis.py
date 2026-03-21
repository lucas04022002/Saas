from datetime import datetime

from pydantic import BaseModel


class AnalysisListOut(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    confidence_score: float
    recommended_bet: str
    bookmaker_odds: float
    value_percent: float
    risk_level: str
    ai_explanation: str
    created_at: datetime
