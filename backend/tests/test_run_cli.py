from datetime import datetime, timezone

from app.collectors.run import quarantine_report
from app.models.enums import MatchStatus
from app.models.match import Match


def _quarantine(db, competition, home, away, kickoff):
    m = Match(competition=competition, league="x", country="x", home_team=home, away_team=away,
              kickoff_at=kickoff, status=MatchStatus.QUARANTINE)
    db.add(m); db.commit()
    return m


def test_quarantine_report_is_empty_without_quarantined_matches(db):
    assert quarantine_report(db) == {}


def test_quarantine_report_groups_by_competition_with_count_and_first_kickoff(db):
    _quarantine(db, "E0", "FC Nulle Part", "Un Inconnu", datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc))
    _quarantine(db, "E0", "FC Nulle Part", "Autre Inconnu", datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc))
    _quarantine(db, "F1", "Club Fantome", "Second Club", datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc))

    report = quarantine_report(db)

    assert set(report) == {"E0", "F1"}
    e0 = {e["name"]: e for e in report["E0"]}
    assert set(e0) == {"FC Nulle Part", "Un Inconnu", "Autre Inconnu"}
    assert e0["FC Nulle Part"]["count"] == 2   # apparaît dans les deux matchs quarantaine E0
    assert e0["FC Nulle Part"]["first_kickoff"].replace(tzinfo=timezone.utc) == datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    assert e0["Un Inconnu"]["count"] == 1
    f1 = {e["name"]: e for e in report["F1"]}
    assert f1["Club Fantome"]["count"] == 1 and f1["Second Club"]["count"] == 1
