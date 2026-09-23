"""Réparation de la base de production : la sélection d'Andorre rattachée au club FC Andorra (23/09/2026).

`seed_aliases` ne corrige pas un alias existant (il est idempotent par construction) : la base de
production garde la mauvaise association. Cette réparation la reproduit ici telle qu'elle est là-bas,
puis vérifie qu'elle est défaite sans rien casser d'autre."""
from datetime import datetime, timezone

from app.collectors.repairs import separer_andorre
from app.models.match import Match
from app.models.team import Team, TeamAlias


def _etat_de_production(db):
    club = Team(name="Andorra", country="Espagne")
    selection = Team(name="Andorre", country="Sélections")
    malte = Team(name="Malte", country="Sélections")
    cadix = Team(name="Cadiz", country="Espagne")
    db.add_all([club, selection, malte, cadix]); db.flush()
    for source in ("fd_uk", "fd_org", "odds_api"):
        db.add(TeamAlias(source=source, alias="andorra", team_id=club.id))
        db.add(TeamAlias(source=source, alias="andorre", team_id=selection.id))
    k = datetime(2026, 9, 24, 18, 45, tzinfo=timezone.utc)
    nl = Match(competition="NL", league="Ligue des Nations", country="Europe", home_team_id=club.id, away_team_id=malte.id,
               home_team="Andorra", away_team="Malte", kickoff_at=k)
    liga = Match(competition="SP2", league="Liga 2", country="Espagne", home_team_id=club.id, away_team_id=cadix.id,
                 home_team="Andorra", away_team="Cadiz", kickoff_at=k)
    db.add_all([nl, liga]); db.commit()
    return club, selection, nl, liga


def test_la_selection_recupere_ses_matchs_et_le_club_garde_les_siens(db):
    club, selection, nl, liga = _etat_de_production(db)

    separer_andorre(db)

    db.refresh(club); db.refresh(nl); db.refresh(liga)
    assert club.name == "FC Andorra"
    assert nl.home_team_id == selection.id and nl.home_team == "Andorre"
    assert liga.home_team_id == club.id and liga.home_team == "FC Andorra"


def test_l_alias_odds_api_pointe_vers_la_selection_et_fd_uk_vers_le_club(db):
    club, selection, *_ = _etat_de_production(db)
    separer_andorre(db)
    par = {(a.source, a.alias): a.team_id for a in db.query(TeamAlias).filter_by(alias="andorra")}
    assert par[("odds_api", "andorra")] == selection.id
    assert par[("fd_uk", "andorra")] == club.id
    assert ("fd_org", "andorra") not in par


def test_la_reparation_est_idempotente_et_sans_effet_sur_une_base_saine(db):
    _etat_de_production(db)
    separer_andorre(db)
    avant = {(m.id, m.home_team_id, m.home_team) for m in db.query(Match)}
    separer_andorre(db)
    assert {(m.id, m.home_team_id, m.home_team) for m in db.query(Match)} == avant


def test_sans_club_andorra_la_reparation_ne_fait_rien(db):
    separer_andorre(db)
    assert db.query(Team).count() == 0


def test_la_migration_0010_tourne_dans_la_transaction_d_alembic(monkeypatch):
    """Le chemin qui peut faire tomber l'API : les migrations tournent au démarrage du conteneur, dans une
    transaction ouverte par Alembic. Si la 0010 échoue, uvicorn ne démarre pas."""
    import importlib.util
    from pathlib import Path

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.database import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        trans = conn.begin()                      # la transaction d'Alembic
        _etat_de_production(Session(bind=conn))

        chemin = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0010_separer_andorre.py"
        spec = importlib.util.spec_from_file_location("m0010", chemin)
        m0010 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m0010)
        monkeypatch.setattr(m0010.op, "get_bind", lambda: conn, raising=False)

        m0010.upgrade()
        trans.commit()                            # Alembic valide à la fin

    with Session(engine) as s:
        assert s.query(Team).filter_by(name="FC Andorra").one().country == "Espagne"
        nl = s.query(Match).filter_by(competition="NL").one()
        assert nl.home_team == "Andorre"
