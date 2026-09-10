from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import make_match

NOW = datetime.now(timezone.utc)


def finished(db, h, a, hg, ag, kick, pinnacle):
    m = make_match(db, h, a, kickoff=kick, status=MatchStatus.FINISHED, home_score=hg, away_score=ag)
    db.add(OddsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=kick - timedelta(hours=2), home=pinnacle[0], draw=pinnacle[1], away=pinnacle[2]))
    # un relevé APRÈS le coup d'envoi ne doit jamais servir
    db.add(OddsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=kick + timedelta(hours=1), home=9.0, draw=9.0, away=1.1))
    db.commit(); return m


def test_track_record_counts_fd_uk_only_matches(client, db):
    """Un match qui n'a que l'archive football-data.co.uk (pas de relevé pinnacle live) doit compter."""
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    kick = NOW - timedelta(days=10)
    m = make_match(db, h, a, kickoff=kick, status=MatchStatus.FINISHED, home_score=2, away_score=0)
    db.add(OddsSnapshot(match_id=m.id, bookmaker="fd_uk_pinnacle", taken_at=kick - timedelta(hours=1), home=1.8, draw=3.6, away=4.2))
    db.commit()
    d = client.get("/api/v1/track-record").json()["data"]
    assert d["items"] == [{"competition": "E0", "played": 1, "favourite_won": 1, "favourite_rate": 1.0}]


def test_track_record_counts_favourite_wins_from_last_pre_kickoff_snapshot(client, db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    finished(db, h, a, 2, 0, NOW - timedelta(days=10), (1.8, 3.6, 4.2))   # favori domicile, gagné
    finished(db, a, h, 0, 0, NOW - timedelta(days=5), (1.8, 3.6, 4.2))    # favori domicile, nul → perdu
    make_match(db, h, a, kickoff=NOW - timedelta(days=2), status=MatchStatus.FINISHED, home_score=1, away_score=0)   # sans relevé : ignoré
    d = client.get("/api/v1/track-record").json()["data"]
    assert d["items"] == [{"competition": "E0", "played": 2, "favourite_won": 1, "favourite_rate": 0.5}]
    assert "c'est le marché" in d["note"]
    assert client.get("/api/v1/track-record?competition=F1").json()["data"]["items"] == []
