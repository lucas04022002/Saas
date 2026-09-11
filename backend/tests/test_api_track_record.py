from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from app.models.totals_snapshot import TotalsSnapshot
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


def test_track_record_exact_score_rate_over_finished_matches(client, db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    # favori domicile net (1.50/4.20/6.50) -> score en tête attendu 1-0 (voir test_engine_score) : match réel 1-0, touché
    finished(db, h, a, 1, 0, NOW - timedelta(days=10), (1.50, 4.20, 6.50))
    # même lecture marché, résultat réel différent (2-1) : pas exact, mais bon vainqueur (domicile)
    finished(db, h, a, 2, 1, NOW - timedelta(days=5), (1.50, 4.20, 6.50))
    d = client.get("/api/v1/track-record").json()["data"]
    assert d["n_scored"] == 2
    assert d["exact_score_rate"] == 0.5
    assert d["winner_rate_from_score"] == 1.0
    assert "score_note" in d and "score exact" in d["score_note"]


def test_track_record_score_fields_null_without_finished_matches(client, db):
    d = client.get("/api/v1/track-record").json()["data"]
    assert d["n_scored"] == 0
    assert d["exact_score_rate"] is None
    assert d["winner_rate_from_score"] is None


def test_track_record_score_uses_closing_totals_snapshot_before_kickoff(client, db):
    """Le score recalculé pour le track record doit utiliser le total de buts du marché (relevé de clôture,
    avant coup d'envoi) quand il est disponible, comme la lecture 1N2 ci-dessus — jamais un relevé posté après."""
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    kick = NOW - timedelta(days=10)
    m = finished(db, h, a, 1, 0, kick, (1.50, 4.20, 6.50))
    baseline = client.get("/api/v1/track-record").json()["data"]
    assert baseline["exact_score_rate"] == 1.0   # score réel 1-0 = score en tête (repli sur la ligue)

    # relevé de clôture très incliné vers l'over : fait basculer le score en tête vers 2-1
    db.add(TotalsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=kick - timedelta(hours=2), line=2.5, over=1.30, under=3.55))
    # un relevé APRÈS le coup d'envoi ne doit jamais servir
    db.add(TotalsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=kick + timedelta(hours=1), line=2.5, over=1.01, under=50.0))
    db.commit()

    d = client.get("/api/v1/track-record").json()["data"]
    assert d["exact_score_rate"] == 0.0          # score en tête devenu 2-1, ne touche plus le résultat réel 1-0
    assert d["winner_rate_from_score"] == 1.0    # toujours favori domicile (2-1)


def test_track_record_accepts_el_competition_filter(client, db):
    """EL (Ligue Europa) doit être une valeur acceptée par le filtre, même sans match résultat."""
    r = client.get("/api/v1/track-record?competition=EL")
    assert r.status_code == 200
    assert r.json()["data"]["items"] == []
