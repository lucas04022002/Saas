from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.bet import Bet
from app.models.enums import BetStatus, MatchStatus, Outcome


def _result(hg: int, ag: int) -> Outcome:
    return Outcome.HOME if hg > ag else Outcome.AWAY if ag > hg else Outcome.DRAW


def settle_bets(db: Session, user_id=None) -> int:
    q = select(Bet).where(Bet.status == BetStatus.PENDING).options(joinedload(Bet.match))
    if user_id is not None:
        q = q.where(Bet.user_id == user_id)
    n = 0
    for bet in db.scalars(q).unique().all():
        m = bet.match
        if m.status != MatchStatus.FINISHED or m.home_score is None or m.away_score is None:
            continue
        won = _result(m.home_score, m.away_score) == bet.outcome
        bet.status = BetStatus.WON if won else BetStatus.LOST
        bet.payout = round(bet.stake * bet.odds, 2) if won else 0.0
        bet.settled_at = datetime.now(timezone.utc)
        n += 1
    db.commit()
    return n
