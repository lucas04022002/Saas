"""Compter les arrivées par réseau et faire le bilan visites → inscriptions → abonnés (01/10/2026)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.access import is_pro
from app.core.sources import SOURCES
from app.models.source_visit import SourceVisit
from app.models.user import User

PARIS = ZoneInfo("Europe/Paris")


def aujourdhui() -> date:
    return datetime.now(PARIS).date()


def compter_visite(db: Session, source: str, jour: date | None = None) -> None:
    """+1 au compteur (jour, source). Deux arrivées simultanées le premier jour : l'une crée la ligne,
    l'autre tombe sur la clé déjà prise et refait l'incrément."""
    jour = jour or aujourdhui()
    plus_un = (update(SourceVisit).where(SourceVisit.day == jour, SourceVisit.source == source)
               .values(visits=SourceVisit.visits + 1))
    if db.execute(plus_un).rowcount:
        db.commit()
        return
    db.add(SourceVisit(day=jour, source=source, visits=1))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        db.execute(plus_un)
        db.commit()


def bilan(db: Session, depuis: date | None = None, now: datetime | None = None) -> list[dict]:
    """Une ligne par source posée (+ « sans lien » pour les inscriptions sans source) :
    visites, inscriptions, abonnés payants aujourd'hui. `depuis` (inclus, heure de Paris) filtre
    visites et inscriptions ; les abonnés sont comptés parmi les inscrits de la période."""
    q = select(SourceVisit.source, func.sum(SourceVisit.visits)).group_by(SourceVisit.source)
    if depuis:
        q = q.where(SourceVisit.day >= depuis)
    visites = {s: int(n or 0) for s, n in db.execute(q)}

    uq = select(User).options(selectinload(User.subscription))
    if depuis:
        uq = uq.where(User.created_at >= datetime.combine(depuis, datetime.min.time(), PARIS))
    inscrits: dict[str | None, list[User]] = {}
    for u in db.scalars(uq):
        inscrits.setdefault(u.signup_source, []).append(u)

    lignes = []
    for s in (*SOURCES, None):
        us = inscrits.get(s, [])
        v = visites.get(s, 0) if s else None
        if s and not v and not us:
            continue  # réseau jamais utilisé : pas de ligne vide
        if s is None and not us:
            continue
        lignes.append({"source": s or "sans lien", "visites": v, "inscriptions": len(us),
                       "abonnes": sum(1 for u in us if is_pro(u, now))})
    return lignes
