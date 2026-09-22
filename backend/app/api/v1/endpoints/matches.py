import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user_optional, get_db
from app.collectors.competitions import COMPETITION_PATTERN
from app.core.access import (
    can_unlock,
    gate_detail,
    gate_list,
    is_pro,
    quota_for,
    unlocked_match_ids,
)
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.match_unlock import MatchUnlock
from app.models.user import User
from app.services.market_reading import match_detail, match_summary

router = APIRouter(prefix="/matches", tags=["matches"])
VISIBLE = (MatchStatus.SCHEDULED, MatchStatus.LIVE, MatchStatus.FINISHED, MatchStatus.POSTPONED)
PARIS = ZoneInfo("Europe/Paris")


def _paris_day_utc_bounds(d: date) -> tuple[datetime, datetime]:
    """Bornes UTC [début, fin] du jour `d` compté en heure de Paris (00:00-24:00 Paris), pas en UTC — un match
    à 22:30 UTC le 11 (00:30 CEST le 12) doit apparaître sous date=12, pas sous date=11."""
    start = datetime.combine(d, time.min, tzinfo=PARIS).astimezone(timezone.utc)
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=PARIS).astimezone(timezone.utc) - timedelta(microseconds=1)
    return start, end


@router.get("")
def list_matches(
    match_date: date | None = Query(default=None, alias="date"),
    competition: str | None = Query(default=None, pattern=COMPETITION_PATTERN),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    q = select(Match).where(Match.status.in_(VISIBLE)).options(selectinload(Match.snapshots), selectinload(Match.totals))
    if match_date:
        day_start, day_end = _paris_day_utc_bounds(match_date)
        q = q.where(Match.kickoff_at >= day_start, Match.kickoff_at <= day_end)
    else:
        now = datetime.now(timezone.utc)
        q = q.where(Match.status == MatchStatus.SCHEDULED, Match.kickoff_at >= now - timedelta(hours=3), Match.kickoff_at <= now + timedelta(days=7))
    if competition:
        q = q.where(Match.competition == competition)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Match.kickoff_at.asc()).offset((page - 1) * limit).limit(limit)).unique().all()
    ouverts = unlocked_match_ids(current_user, db)
    items = gate_list([match_summary(db, m) for m in rows], current_user, ouverts)
    return {
        "success": True,
        "message": "Matches fetched",
        "data": {
            "items": items,
            "pagination": {"page": page, "limit": limit, "total": total},
            # Le client affiche « il te reste N matchs cette semaine » sans avoir
            # à compter lui-même : le serveur seul sait ce qui a été dépensé.
            "quota": quota_for(current_user, db),
        },
    }


@router.get("/next")
def next_match_day(
    after: date = Query(...),
    competition: str | None = Query(default=None, pattern=COMPETITION_PATTERN),
    db: Session = Depends(get_db),
):
    """Le premier jour (heure de Paris) strictement après `after` qui a au moins un match programmé.

    Un jour vide ne doit pas être un cul-de-sac : un visiteur arrivé un mardi de trêve internationale
    voyait « Aucun match ce jour-là » et repartait, alors que la Ligue des Nations reprenait jeudi
    (22/09/2026). Déclaré avant `/{match_id}`, sinon « next » serait pris pour un identifiant.
    """
    _, fin_du_jour = _paris_day_utc_bounds(after)
    q = select(Match).where(Match.status == MatchStatus.SCHEDULED, Match.kickoff_at > fin_du_jour,
                            Match.kickoff_at <= fin_du_jour + timedelta(days=60))
    if competition:
        q = q.where(Match.competition == competition)
    premier = db.scalar(q.order_by(Match.kickoff_at.asc()).limit(1))
    if premier is None:
        return {"success": True, "message": "", "data": None}
    kickoff = premier.kickoff_at if premier.kickoff_at.tzinfo else premier.kickoff_at.replace(tzinfo=timezone.utc)
    jour = kickoff.astimezone(PARIS).date()
    debut, fin = _paris_day_utc_bounds(jour)
    qj = select(Match).where(Match.status == MatchStatus.SCHEDULED, Match.kickoff_at >= debut, Match.kickoff_at <= fin)
    if competition:
        qj = qj.where(Match.competition == competition)
    du_jour = db.scalars(qj).all()
    return {"success": True, "message": "", "data": {
        "date": jour.isoformat(),
        "count": len(du_jour),
        "competitions": sorted({m.competition for m in du_jour}),
    }}


@router.get("/{match_id}")
def get_match(match_id: str, db: Session = Depends(get_db), current_user: User | None = Depends(get_current_user_optional)):
    try:
        match_uuid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match not found")
    row = db.scalar(select(Match).where(Match.id == match_uuid).options(selectinload(Match.snapshots), selectinload(Match.totals)))
    if row is None or row.status == MatchStatus.QUARANTINE:
        raise HTTPException(status_code=404, detail="Match not found")
    ouverts = unlocked_match_ids(current_user, db)
    detail = match_detail(db, row, public=not is_pro(current_user))
    detail = gate_detail(detail, current_user, ouverts)
    # Le quota vit DANS `data` : le client ne lit que cette clé de l'enveloppe,
    # et un quota posé à côté serait silencieusement perdu.
    detail["quota"] = quota_for(current_user, db)
    return {"success": True, "message": "Match detail fetched", "data": detail}


@router.post("/{match_id}/unlock")
def unlock_match(
    match_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Dépense un crédit hebdomadaire pour ouvrir un match.

    Une action explicite, et non un effet de bord de la lecture : le
    préchargement de Next.js au survol d'un lien viderait sinon le quota de
    l'utilisateur avant qu'il ait cliqué.

    Rejouer l'appel sur un match déjà ouvert ne coûte rien et répond comme la
    première fois : deux onglets, ou un double clic, ne doivent pas coûter deux
    crédits.
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Créez un compte gratuit pour ouvrir un match.")

    try:
        match_uuid = uuid.UUID(match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match not found")

    row = db.scalar(select(Match).where(Match.id == match_uuid))
    if row is None or row.status == MatchStatus.QUARANTINE:
        raise HTTPException(status_code=404, detail="Match not found")

    if is_pro(current_user):
        return {"success": True, "message": "Inclus dans l'abonnement", "data": quota_for(current_user, db)}

    deja = db.scalar(
        select(MatchUnlock).where(
            MatchUnlock.user_id == current_user.id, MatchUnlock.match_id == match_uuid
        )
    )
    if deja is None:
        if not can_unlock(current_user, db):
            raise HTTPException(
                status_code=402,
                detail="Vous avez ouvert vos matchs de la semaine. Le quota se recharge lundi.",
            )
        db.add(MatchUnlock(user_id=current_user.id, match_id=match_uuid))
        db.commit()

    return {"success": True, "message": "Match ouvert", "data": quota_for(current_user, db)}
