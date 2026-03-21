from datetime import datetime

from pydantic import BaseModel


class FavoriteOut(BaseModel):
    id: str
    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff_at: datetime
    created_at: datetime
