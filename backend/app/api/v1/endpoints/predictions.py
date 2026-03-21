from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.prediction_service import prediction_service

router = APIRouter(prefix="/predictions", tags=["predictions"])
limiter = Limiter(key_func=get_remote_address)


class PredictRequest(BaseModel):
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)
    league: str | None = None


@router.post("/match")
@limiter.limit("60/hour")
def predict_match(request: Request, payload: PredictRequest):
    prediction = prediction_service.get_prediction(payload.home_team, payload.away_team, payload.league)
    return {"success": True, "message": "Prediction generated successfully", "data": prediction}


@router.get("/health")
def prediction_health():
    return {"success": True, "message": "Prediction provider is healthy", "data": prediction_service.health()}
