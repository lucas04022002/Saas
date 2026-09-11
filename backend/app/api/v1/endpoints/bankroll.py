import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.bet import Bet
from app.models.enums import BetStatus, MatchStatus, Outcome
from app.models.match import Match
from app.models.user import User
from app.services.settlement import settle_bets

router = APIRouter(prefix="/bankroll", tags=["bankroll"])


class BetIn(BaseModel):
    match_id: str
    outcome: Outcome
    bookmaker: str = Field(min_length=2, max_length=40)
    odds: float = Field(gt=1.0, le=1000)
    stake: float = Field(gt=0, le=100000)


def _bet_dict(b: Bet) -> dict:
    return {"id": str(b.id), "match_id": str(b.match_id), "home_team": b.match.home_team, "away_team": b.match.away_team,
            "competition": b.match.competition, "kickoff_at": b.match.kickoff_at, "outcome": b.outcome.value, "bookmaker": b.bookmaker,
            "odds": b.odds, "stake": b.stake, "status": b.status.value, "payout": b.payout, "created_at": b.created_at, "settled_at": b.settled_at,
            "match_status": b.match.status.value}


def _summary(bets: list[Bet]) -> dict:
    settled = [b for b in bets if b.status in (BetStatus.WON, BetStatus.LOST)]
    stakes = sum(b.stake for b in bets); settled_stakes = sum(b.stake for b in settled); payouts = sum(b.payout or 0 for b in settled)
    def bucket(key):
        acc: dict = defaultdict(lambda: {"stakes": 0.0, "payouts": 0.0, "profit": 0.0, "bets": 0})
        for b in settled:
            k = key(b); acc[k]["stakes"] += b.stake; acc[k]["payouts"] += b.payout or 0; acc[k]["bets"] += 1
            acc[k]["profit"] = round(acc[k]["payouts"] - acc[k]["stakes"], 2)
        return dict(acc)
    return {"stakes": stakes, "settled_stakes": settled_stakes, "payouts": payouts, "profit": round(payouts - settled_stakes, 2), "roi": round((payouts - settled_stakes) / settled_stakes, 4) if settled_stakes else None,
            "pending": sum(1 for b in bets if b.status == BetStatus.PENDING), "settled": len(settled),
            "by_bookmaker": bucket(lambda b: b.bookmaker), "by_competition": bucket(lambda b: b.match.competition)}


@router.get("")
def list_bets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_bets(db, user_id=current_user.id)
    bets = db.scalars(select(Bet).where(Bet.user_id == current_user.id).options(joinedload(Bet.match)).order_by(Bet.created_at.desc())).unique().all()
    return {"success": True, "message": "Bankroll fetched", "data": {"items": [_bet_dict(b) for b in bets], "summary": _summary(bets)}}


@router.post("", status_code=201)
def create_bet(payload: BetIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        match_id = uuid.UUID(payload.match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match not found")
    match = db.get(Match, match_id)
    if match is None or match.status == MatchStatus.QUARANTINE:
        raise HTTPException(status_code=404, detail="Match not found")
    bet = Bet(user_id=current_user.id, match_id=match.id, outcome=payload.outcome, bookmaker=payload.bookmaker, odds=payload.odds, stake=payload.stake)
    db.add(bet); db.commit(); db.refresh(bet)
    return {"success": True, "message": "Bet recorded", "data": _bet_dict(bet)}


def _own_bet(db: Session, bet_id: str, user: User) -> Bet:
    try:
        bet_uuid = uuid.UUID(bet_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bet not found")
    bet = db.scalar(select(Bet).where(Bet.id == bet_uuid, Bet.user_id == user.id).options(joinedload(Bet.match)))
    if bet is None:
        raise HTTPException(status_code=404, detail="Bet not found")
    return bet


@router.delete("/{bet_id}")
def delete_bet(bet_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bet = _own_bet(db, bet_id, current_user)
    if bet.status != BetStatus.PENDING:
        raise HTTPException(status_code=409, detail="Only pending bets can be deleted")
    db.delete(bet); db.commit()
    return {"success": True, "message": "Bet deleted", "data": {"id": bet_id}}


@router.post("/{bet_id}/void")
def void_bet(bet_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bet = _own_bet(db, bet_id, current_user)
    if bet.status != BetStatus.PENDING or bet.match.status != MatchStatus.POSTPONED:
        raise HTTPException(status_code=409, detail="Only pending bets on postponed matches can be voided")
    bet.status, bet.payout, bet.settled_at = BetStatus.VOID, bet.stake, datetime.now(timezone.utc)
    db.commit(); db.refresh(bet)
    return {"success": True, "message": "Bet voided", "data": _bet_dict(bet)}
