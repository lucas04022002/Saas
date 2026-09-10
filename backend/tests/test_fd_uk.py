from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.collectors.aliases import normalize, seed_aliases
from app.collectors.fd_uk import import_rows, parse_csv
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team, TeamAlias
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


def test_quarantine_recovers_canonical_team_after_alias_added(db):
    seed_aliases(db)
    rows = parse_csv(SAMPLE)
    row = next(r for r in rows if r.home == "FC Nulle Part")

    report = import_rows(db, "E0", [row])
    assert report.quarantined == 1
    q = db.query(Match).filter(Match.status == MatchStatus.QUARANTINE).one()
    assert q.home_team_id is None

    arsenal = db.query(Team).filter(Team.name == "Arsenal").one()
    db.add(TeamAlias(source="fd_uk", alias=normalize("FC Nulle Part"), team_id=arsenal.id))
    db.commit()

    report2 = import_rows(db, "E0", [row])

    assert report2.quarantined == 0 and report2.updated == 1
    assert db.query(Match).count() == 1
    m = db.query(Match).one()
    bournemouth = db.query(Team).filter(Team.name == "Bournemouth").one()
    assert m.status == MatchStatus.FINISHED
    assert (m.home_score, m.away_score) == (4, 2)
    assert m.home_team_id == arsenal.id and m.away_team_id == bournemouth.id
    assert m.home_team == "Arsenal" and m.away_team == "Bournemouth"


def test_missing_time_falls_back_to_15h_utc_kickoff_and_14h_closing(db):
    seed_aliases(db)
    rows = parse_csv(SAMPLE)
    row = next(r for r in rows if r.home == "Fulham" and r.away == "Everton")
    assert row.time is None

    import_rows(db, "E0", [row])

    m = db.query(Match).filter(Match.home_team == "Fulham", Match.away_team == "Everton").one()
    assert m.kickoff_at.replace(tzinfo=timezone.utc) == datetime(2025, 8, 31, 15, 0, tzinfo=timezone.utc)
    closing = [s for s in db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id)
               if s.taken_at.replace(tzinfo=timezone.utc) == datetime(2025, 8, 31, 14, 0, tzinfo=timezone.utc)]
    assert len(closing) == 2   # avg + pinnacle, clôture = coup d'envoi (15:00) − 1h


def test_closing_snapshot_not_duplicated_after_kickoff_correction_by_fd_org(db):
    """fd_org peut réécrire match.kickoff_at (heure exacte) ; la clôture fd_uk doit rester datée depuis la ligne CSV,
    pas depuis match.kickoff_at, sinon un second import archive la même clôture à un nouvel horodatage."""
    seed_aliases(db)
    import_rows(db, "E0", parse_csv(SAMPLE)[:1])
    m = db.query(Match).filter(Match.home_team == "Liverpool").one()
    before = db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id).count()

    m.kickoff_at = m.kickoff_at - timedelta(hours=1)   # simulate fd_org correction
    db.commit()

    import_rows(db, "E0", parse_csv(SAMPLE)[:1])

    after = db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id).count()
    assert after == before
