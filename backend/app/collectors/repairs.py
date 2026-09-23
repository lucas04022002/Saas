"""Réparations ponctuelles de la base de production, testées et appelées par une migration.

`seed_aliases` est idempotent par construction : il n'écrase jamais un alias existant. Quand un alias
a été posé vers la mauvaise équipe, seule une réparation explicite peut le défaire.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team, TeamAlias

log = logging.getLogger("rushplay.repairs")

SELECTIONS = "Sélections"


def separer_andorre(db: Session) -> None:
    """Défait la confusion entre le club FC Andorra (Liga 2) et la sélection d'Andorre (22-23/09/2026).

    Le club avait été ajouté sous le nom canonique « Andorra », alias implicite pour toutes les sources ;
    The Odds API écrit la sélection « Andorra » aussi. Le premier servi a gagné : le relevé de la Ligue des
    Nations a rattaché la sélection au club. Idempotent ; sans effet sur une base qui n'a pas le défaut.
    """
    club = db.scalar(select(Team).where(Team.name.in_(["Andorra", "FC Andorra"]), Team.country == "Espagne"))
    if club is None:
        return

    selection = db.scalar(select(Team).where(Team.name == "Andorre", Team.country == SELECTIONS))
    if selection is None:
        selection = Team(id=uuid.uuid4(), name="Andorre", country=SELECTIONS)
        db.add(selection)
        db.flush()

    # 1. le club prend son vrai nom, et ses matchs de championnat l'affichent
    club.name = "FC Andorra"
    championnat = select(Match).where(Match.competition != "NL",
                                      or_(Match.home_team_id == club.id, Match.away_team_id == club.id))
    for m in db.scalars(championnat):
        if m.home_team_id == club.id:
            m.home_team = "FC Andorra"
        if m.away_team_id == club.id:
            m.away_team = "FC Andorra"

    # 2. les matchs de sélections rattachés au club reviennent à la sélection
    deplaces = 0
    selections = select(Match).where(Match.competition == "NL",
                                     or_(Match.home_team_id == club.id, Match.away_team_id == club.id))
    for m in db.scalars(selections):
        if m.home_team_id == club.id:
            m.home_team_id, m.home_team = selection.id, "Andorre"
        if m.away_team_id == club.id:
            m.away_team_id, m.away_team = selection.id, "Andorre"
        deplaces += 1

    # 3. alias : fd_uk « Andorra » reste au club ; odds_api « Andorra » va à la sélection ; fd_org n'en a pas l'usage
    for a in db.scalars(select(TeamAlias).where(TeamAlias.alias == "andorra")).all():
        if a.source == "odds_api":
            a.team_id = selection.id
        elif a.source == "fd_org":
            db.delete(a)
    db.flush()
    if db.scalar(select(TeamAlias).where(TeamAlias.source == "odds_api", TeamAlias.alias == "andorra")) is None:
        db.add(TeamAlias(source="odds_api", alias="andorra", team_id=selection.id))

    db.commit()
    log.warning("Andorre : club renommé FC Andorra, %s match(s) de sélection réattribué(s)", deplaces)
