import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.core.time import to_utc_iso
from app.models.enums import MatchStatus
from app.models.favorite import Favorite
from app.models.match import Match
from app.models.user import User

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("")
def list_favorites(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .options(joinedload(Favorite.match))
        .order_by(Favorite.created_at.desc())
    ).all()

    data = [
        {
            "id": str(item.id),
            "match_id": str(item.match_id),
            "home_team": item.match.home_team,
            "away_team": item.match.away_team,
            "league": item.match.league,
            "kickoff_at": to_utc_iso(item.match.kickoff_at),
            "created_at": to_utc_iso(item.created_at),
        }
        for item in rows
    ]

    return {"success": True, "message": "Favorites fetched successfully", "data": data}


@router.post("/{match_id}")
def add_favorite(match_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        match_uuid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match not found")
    match = db.get(Match, match_uuid)
    if match is None or match.status == MatchStatus.QUARANTINE:
        raise HTTPException(status_code=404, detail="Match not found")

    favorite = Favorite(user_id=current_user.id, match_id=match.id)
    db.add(favorite)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Favorite already exists")

    return {"success": True, "message": "Favorite added", "data": {"match_id": str(match.id)}}


@router.delete("/{match_id}")
def delete_favorite(match_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        match_uuid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match not found")
    favorite = db.scalar(select(Favorite).where(Favorite.user_id == current_user.id, Favorite.match_id == match_uuid))
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()
    return {"success": True, "message": "Favorite removed", "data": {"match_id": match_id}}
