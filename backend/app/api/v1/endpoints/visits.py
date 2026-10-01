"""`POST /api/v1/visits` : le navigateur signale une arrivée par le lien d'un réseau (`?ref=tiktok`).

Public et anonyme : rien n'est lu sauf la source. Une source hors de la liste fermée est ignorée en
silence (même réponse), pour ne rien apprendre à qui teste des valeurs. Limité par adresse, pour qu'un
script ne gonfle pas les chiffres d'un réseau.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.client_ip import limiter
from app.core.sources import source_valide
from app.services.sources import compter_visite

router = APIRouter(prefix="/visits", tags=["visits"], include_in_schema=False)


class VisitRequest(BaseModel):
    source: str = Field(max_length=32)


@router.post("")
@limiter.limit("20/hour")
def visit(request: Request, payload: VisitRequest, db: Session = Depends(get_db)):
    source = source_valide(payload.source)
    if source:
        compter_visite(db, source)
    return {"success": True, "message": "ok", "data": None}
