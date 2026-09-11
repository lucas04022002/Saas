from datetime import datetime, timedelta, timezone

from app.collectors import run as run_cli
from app.collectors.aliases import seed_aliases
from app.collectors.run import quarantine_report
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.team import Team
from tests.conftest import make_match


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


def test_cli_dedup_runs_dedup_matches_and_writes_heartbeat(db, monkeypatch):
    """La commande CLI dedup route bien vers dedup_matches et écrit le heartbeat (sans toucher au vrai dossier
    heartbeats/ ni à un dev.db réel : get_db et write_heartbeat sont monkeypatchés vers la session de test)."""
    monkeypatch.setattr(run_cli, "get_db", lambda: iter([db]))
    written = {}
    monkeypatch.setattr(run_cli, "write_heartbeat", lambda name, summary: written.update(name=name, summary=summary))

    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    kickoff = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
    make_match(db, h, a, competition="E0", kickoff=kickoff)
    make_match(db, h, a, competition="E0", kickoff=kickoff + timedelta(hours=1))

    code = run_cli.main(["dedup"])

    assert code == 0
    assert written["name"] == "dedup"
    assert written["summary"] == {"groups": 1, "removed": 1}
    assert db.query(Match).filter(Match.competition == "E0").count() == 1
