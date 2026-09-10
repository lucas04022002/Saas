import json
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.aliases import seed_aliases
from app.collectors.fd_org import import_matches, parse_matches
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.team import Team
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
