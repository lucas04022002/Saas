from datetime import datetime

from pydantic import BaseModel


class OpportunityOut(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff_at: datetime
    confidence_score: float
    recommended_bet: str
    bookmaker_odds: float
    value_percent: float
    risk_level: str
    short_ai_explanation: str
