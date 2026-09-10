import json
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.aliases import normalize, seed_aliases
from app.collectors.fd_org import import_matches, parse_matches
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.team import Team, TeamAlias
from tests.conftest import make_match

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "fd_org_matches.json").read_text(encoding="utf-8"))


def test_parse_maps_status_and_scores():
    items = parse_matches(PAYLOAD)
    assert [i.status for i in items] == ["TIMED", "FINISHED", "POSTPONED", "TIMED"]
    assert items[1].hg == 2 and items[1].ag == 0 and items[0].hg is None
    assert items[0].utc_date == datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc)
    assert items[0].competition_code == "E0" and items[0].ext_id == "fdo:537001"


def test_import_creates_scheduled_finished_postponed_and_quarantine(db):
    seed_aliases(db)
    report = import_matches(db, parse_matches(PAYLOAD))
    assert (report.created, report.quarantined) == (3, 1)
    by_ext = {m.external_id: m for m in db.query(Match).all()}
    assert by_ext["fdo:537001"].status == MatchStatus.SCHEDULED
    assert by_ext["fdo:537002"].status == MatchStatus.FINISHED and by_ext["fdo:537002"].home_score == 2
    assert by_ext["fdo:537003"].status == MatchStatus.POSTPONED
    assert by_ext["fdo:537004"].status == MatchStatus.QUARANTINE


def test_import_updates_kickoff_of_match_created_by_fd_uk(db):
    """fd_uk crée le match à 15:00 UTC sans heure fiable ; fd_org apporte l'heure exacte et l'id externe."""
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    m = make_match(db, h, a, kickoff=datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc))
    import_matches(db, parse_matches(PAYLOAD)[:1])
    db.refresh(m)
    assert m.external_id == "fdo:537001"
    assert m.kickoff_at.replace(tzinfo=timezone.utc) == datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc)
    assert db.query(Match).count() == 1


def test_import_is_idempotent(db):
    seed_aliases(db)
    import_matches(db, parse_matches(PAYLOAD))
    report = import_matches(db, parse_matches(PAYLOAD))
    assert report.created == 0 and db.query(Match).count() == 4


def test_quarantine_recovers_canonical_team_after_alias_added(db):
    seed_aliases(db)
    item = next(i for i in parse_matches(PAYLOAD) if i.home == "FC Nulle Part")

    report = import_matches(db, [item])
    assert report.quarantined == 1
    q = db.query(Match).filter(Match.status == MatchStatus.QUARANTINE).one()
    assert q.home_team_id is None

    tottenham = db.query(Team).filter(Team.name == "Tottenham").one()
    db.add(TeamAlias(source="fd_org", alias=normalize("FC Nulle Part"), team_id=tottenham.id))
    db.commit()

    report2 = import_matches(db, [item])

    assert report2.quarantined == 0 and report2.updated == 1
    assert db.query(Match).count() == 1
    m = db.query(Match).one()
    everton = db.query(Team).filter(Team.name == "Everton").one()
    assert m.status == MatchStatus.SCHEDULED
    assert m.home_team_id == tottenham.id and m.away_team_id == everton.id
    assert m.home_team == "Tottenham" and m.away_team == "Everton"


def test_malformed_match_is_skipped_others_still_imported(db, caplog):
    seed_aliases(db)
    payload = {
        "competition": {"code": "PL"},
        "matches": [
            {"id": 9001, "utcDate": "nope", "status": "TIMED",
             "homeTeam": {"name": "Arsenal FC"}, "awayTeam": {"name": "Chelsea FC"},
             "score": {"fullTime": {"home": None, "away": None}}},
            {"id": 9002, "utcDate": "2026-09-12T14:00:00Z", "status": "TIMED",
             "homeTeam": {"name": "Liverpool FC"}, "awayTeam": {"name": "AFC Bournemouth"},
             "score": {"fullTime": {"home": None, "away": None}}},
        ],
    }
    items = parse_matches(payload)
    assert len(items) == 1 and items[0].ext_id == "fdo:9002"
    assert any(rec.levelname == "WARNING" for rec in caplog.records)

    report = import_matches(db, items)
    assert report.created == 1
    assert db.query(Match).count() == 1
