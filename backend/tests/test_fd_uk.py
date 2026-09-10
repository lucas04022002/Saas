from datetime import date, datetime, timezone
from pathlib import Path

from app.collectors.aliases import seed_aliases
from app.collectors.fd_uk import import_rows, parse_csv
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import make_match

SAMPLE = (Path(__file__).parent / "fixtures" / "fd_uk_E0_sample.csv").read_text(encoding="utf-8-sig")


def test_parse_csv_reads_scores_shots_and_odds():
    rows = parse_csv(SAMPLE)
    r = rows[0]
    assert (r.date, r.home, r.away, r.hg, r.ag) == (date(2025, 8, 15), "Liverpool", "Bournemouth", 4, 2)
    assert r.hs == 19 and r.as_ == 10
    assert r.avg_open == (1.31, 5.96, 8.31)
    assert r.avg_close is not None and r.ps_close is not None


def test_import_creates_finished_matches_and_two_snapshots(db):
    seed_aliases(db)
    report = import_rows(db, "E0", parse_csv(SAMPLE)[:2])
    assert (report.created, report.quarantined) == (2, 0)
    m = db.query(Match).filter(Match.home_team == "Liverpool").one()
    assert m.status == MatchStatus.FINISHED and (m.home_score, m.away_score) == (4, 2)
    assert m.competition == "E0" and m.home_team_id is not None
    assert m.kickoff_at.replace(tzinfo=timezone.utc) == datetime(2025, 8, 15, 20, 0, tzinfo=timezone.utc)
    books = sorted(s.bookmaker for s in db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id))
    assert books == ["fd_uk_avg", "fd_uk_avg", "fd_uk_pinnacle", "fd_uk_pinnacle"]   # ouverture + clôture × 2 bookmakers
    assert report.snapshots == 8
    closing_snapshots = [
        s for s in db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id)
        if s.taken_at.replace(tzinfo=timezone.utc) == datetime(2025, 8, 15, 19, 0, tzinfo=timezone.utc)
    ]
    assert len(closing_snapshots) == 2   # avg + pinnacle, clôture = coup d'envoi − 1h


def test_import_is_idempotent(db):
    seed_aliases(db)
    import_rows(db, "E0", parse_csv(SAMPLE)[:2])
    report = import_rows(db, "E0", parse_csv(SAMPLE)[:2])
    assert (report.created, report.updated, report.snapshots) == (0, 2, 0)
    assert db.query(Match).count() == 2 and db.query(OddsSnapshot).count() == 8


def test_unknown_team_goes_to_quarantine(db, caplog):
    seed_aliases(db)
    report = import_rows(db, "E0", parse_csv(SAMPLE))
    assert report.quarantined == 1
    q = db.query(Match).filter(Match.status == MatchStatus.QUARANTINE).one()
    assert q.home_team == "FC Nulle Part" and q.home_team_id is None
    assert any("FC Nulle Part" in rec.message and rec.levelname == "WARNING" for rec in caplog.records)


def test_import_reuses_match_created_by_another_source(db):
    seed_aliases(db)
    liverpool = db.query(Team).filter(Team.name == "Liverpool").one()
    bournemouth = db.query(Team).filter(Team.name == "Bournemouth").one()
    existing = make_match(
        db, liverpool, bournemouth, competition="E0",
        kickoff=datetime(2025, 8, 15, 19, 0, tzinfo=timezone.utc),   # même jour, heure différente ; fd_uk_key = None
    )
    assert existing.fd_uk_key is None

    report = import_rows(db, "E0", parse_csv(SAMPLE)[:1])

    assert db.query(Match).count() == 1
    assert report.updated == 1
    db.refresh(existing)
    assert existing.fd_uk_key == "E0:2025-08-15:Liverpool:Bournemouth"
    assert existing.status == MatchStatus.FINISHED
    assert (existing.home_score, existing.away_score) == (4, 2)
    assert db.query(OddsSnapshot).filter(OddsSnapshot.match_id == existing.id).count() == 4


def test_missing_shots_and_closing_odds(db):
    seed_aliases(db)
    rows = parse_csv(SAMPLE)
    row = next(r for r in rows if r.home == "Chelsea")
    assert row.hs is None
    assert row.avg_close is None
    assert row.ps_close is None

    report = import_rows(db, "E0", [row])

    m = db.query(Match).filter(Match.home_team == "Chelsea").one()
    assert m.home_shots is None
    assert report.snapshots == 2
    assert db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id).count() == 2
