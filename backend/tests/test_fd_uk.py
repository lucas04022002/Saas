from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from app.collectors.aliases import normalize, seed_aliases
from app.collectors.fd_uk import import_fixtures, import_rows, parse_csv, parse_fixtures_csv
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team, TeamAlias
from tests.conftest import make_match

SAMPLE = (Path(__file__).parent / "fixtures" / "fd_uk_E0_sample.csv").read_text(encoding="utf-8-sig")
SAMPLE_FIXTURES = (Path(__file__).parent / "fixtures" / "fd_uk_fixtures_sample.csv").read_text(encoding="utf-8-sig")


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


def test_malformed_row_is_skipped_others_still_imported(db, caplog):
    seed_aliases(db)
    csv_text = (
        "Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n"
        "garbage,20:00,Liverpool,Bournemouth,4,2,H\n"
        "17/08/2025,16:30,Man United,Arsenal,abc,1,A\n"
        "15/08/2025,20:00,Chelsea,Fulham,0,1,A\n"
    )
    rows = parse_csv(csv_text)
    assert len(rows) == 1 and rows[0].home == "Chelsea"
    assert sum(1 for rec in caplog.records if rec.levelname == "WARNING") == 2

    report = import_rows(db, "E0", rows)
    assert report.created == 1
    assert db.query(Match).count() == 1


# ---- fixtures.csv (matchs à venir avec cotes, sans score) ----

def test_parse_fixtures_csv_keeps_only_the_five_leagues():
    rows = parse_fixtures_csv(SAMPLE_FIXTURES)
    assert [r.div for r in rows] == ["E0", "F1"]   # la ligne E1 est ignorée
    e0 = rows[0]
    assert (e0.date, e0.time, e0.home, e0.away) == (date(2026, 9, 12), time(15, 0), "Aston Villa", "Nott'm Forest")
    assert e0.avg == (2.22, 3.39, 3.17)
    assert e0.max_ == (2.3, 3.5, 3.25)


def test_import_fixtures_creates_scheduled_match_with_one_avg_snapshot(db):
    seed_aliases(db)
    rows = parse_fixtures_csv(SAMPLE_FIXTURES)
    taken_at = datetime(2026, 9, 11, 10, 30, tzinfo=timezone.utc)

    report = import_fixtures(db, rows, taken_at)

    assert report.created == 1 and report.quarantined == 1
    m = db.query(Match).filter(Match.home_team == "Aston Villa").one()
    assert m.status == MatchStatus.SCHEDULED
    assert m.home_score is None and m.away_score is None
    assert m.competition == "E0" and m.fd_uk_key == "E0:2026-09-12:Aston Villa:Nott'm Forest"
    snaps = db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id).all()
    assert len(snaps) == 1
    assert snaps[0].bookmaker == "fd_uk_avg"
    assert snaps[0].taken_at.replace(tzinfo=timezone.utc) == datetime(2026, 9, 11, 10, 0, tzinfo=timezone.utc)  # arrondi à l'heure
    assert (snaps[0].home, snaps[0].draw, snaps[0].away) == (2.22, 3.39, 3.17)


def test_import_fixtures_quarantines_unknown_team(db):
    seed_aliases(db)
    rows = parse_fixtures_csv(SAMPLE_FIXTURES)
    report = import_fixtures(db, rows, datetime(2026, 9, 11, 10, 30, tzinfo=timezone.utc))

    assert report.quarantined == 1
    q = db.query(Match).filter(Match.status == MatchStatus.QUARANTINE).one()
    assert q.home_team == "FC Nulle Part" and q.home_team_id is None
    assert db.query(OddsSnapshot).filter(OddsSnapshot.match_id == q.id).count() == 0


def test_import_fixtures_quarantine_recovers_canonical_team_after_alias_added(db):
    """Même comportement de récupération que import_rows (via fd_uk_key) : une fois l'alias ajouté et
    seed/l'import relancés, la ligne quarantaine existante est réutilisée et assignée, pas dupliquée."""
    seed_aliases(db)
    rows = parse_fixtures_csv(SAMPLE_FIXTURES)
    row = next(r for r in rows if r.home == "FC Nulle Part")
    taken_at = datetime(2026, 9, 11, 10, 30, tzinfo=timezone.utc)

    report = import_fixtures(db, [row], taken_at)
    assert report.quarantined == 1
    q = db.query(Match).filter(Match.status == MatchStatus.QUARANTINE).one()
    assert q.home_team_id is None

    monaco = db.query(Team).filter(Team.name == "Monaco").one()
    arsenal = db.query(Team).filter(Team.name == "Arsenal").one()
    db.add(TeamAlias(source="fd_uk", alias=normalize("FC Nulle Part"), team_id=arsenal.id))
    db.commit()

    report2 = import_fixtures(db, [row], taken_at)

    assert report2.quarantined == 0 and report2.updated == 1
    assert db.query(Match).count() == 1
    m = db.query(Match).one()
    assert m.status == MatchStatus.SCHEDULED
    assert m.home_team_id == arsenal.id and m.away_team_id == monaco.id
    assert m.home_team == "Arsenal" and m.away_team == "Monaco"
    snaps = db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id).all()
    assert len(snaps) == 1   # la cote est bien archivée une fois le match sorti de la quarantaine


def test_import_fixtures_is_idempotent(db):
    seed_aliases(db)
    rows = parse_fixtures_csv(SAMPLE_FIXTURES)
    taken_at = datetime(2026, 9, 11, 10, 30, tzinfo=timezone.utc)
    import_fixtures(db, rows, taken_at)

    report = import_fixtures(db, rows, taken_at)

    assert (report.created, report.snapshots) == (0, 0)
    assert db.query(Match).filter(Match.status == MatchStatus.SCHEDULED).count() == 1
    assert db.query(OddsSnapshot).count() == 1


def test_import_fixtures_never_downgrades_a_finished_match(db):
    seed_aliases(db)
    villa = db.query(Team).filter(Team.name == "Aston Villa").one()
    forest = db.query(Team).filter(Team.name == "Nottingham Forest").one()
    existing = make_match(
        db, villa, forest, competition="E0",
        kickoff=datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc),
        status=MatchStatus.FINISHED, home_score=2, away_score=1,
    )

    rows = parse_fixtures_csv(SAMPLE_FIXTURES)
    import_fixtures(db, rows, datetime(2026, 9, 11, 10, 30, tzinfo=timezone.utc))

    db.refresh(existing)
    assert existing.status == MatchStatus.FINISHED
    assert (existing.home_score, existing.away_score) == (2, 1)


def test_decode_csv_strips_utf8_bom_even_when_requests_guesses_latin1():
    """Le serveur n'annonce pas de charset : sans ce décodage, la 1re colonne devient « ï»¿Div »."""
    from app.collectors.fd_uk import _decode_csv, parse_fixtures_csv

    class FakeResp:
        content = "﻿Div,Date,Time,HomeTeam,AwayTeam,AvgH,AvgD,AvgA\nE0,12/09/2026,16:00,Arsenal,Chelsea,1.9,3.5,4.0\n".encode("utf-8")
        encoding = "ISO-8859-1"

    text = _decode_csv(FakeResp())
    assert text.startswith("Div,")
    rows = parse_fixtures_csv(text)
    assert len(rows) == 1 and rows[0].home == "Arsenal"
