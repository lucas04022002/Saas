import json
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.aliases import seed_aliases
from app.collectors.odds_api import parse_events, store_events
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import make_match

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "odds_api_epl.json").read_text(encoding="utf-8"))
T0 = datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc)


def test_parse_keeps_french_books_and_pinnacle_only():
    ev = parse_events("soccer_epl", PAYLOAD)[0]
    assert ev.competition_code == "E0" and (ev.home, ev.away) == ("Arsenal", "Chelsea")
    assert set(ev.books) == {"betclic_fr", "winamax_fr", "pinnacle"}      # williamhill écarté
    assert ev.books["betclic_fr"] == (1.95, 3.6, 3.9)                    # ordre domicile, nul, extérieur


def test_store_attaches_snapshots_to_existing_match(db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    m = make_match(db, h, a, kickoff=datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc))
    report = store_events(db, parse_events("soccer_epl", PAYLOAD), taken_at=T0)
    assert (report.matched, report.snapshots, report.quarantined) == (1, 3, 1)
    snaps = db.query(OddsSnapshot).filter_by(match_id=m.id).all()
    assert {s.bookmaker for s in snaps} == {"betclic_fr", "winamax_fr", "pinnacle"} and all(s.taken_at.replace(tzinfo=timezone.utc) == T0 for s in snaps)


def test_store_creates_match_when_calendar_missing(db):
    """Le calendrier fd_org peut être en retard : le match est créé SCHEDULED à partir de l'événement."""
    seed_aliases(db)
    report = store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    assert report.matched == 1
    m = db.query(Match).filter(Match.status == MatchStatus.SCHEDULED).one()
    assert (m.home_team, m.away_team, m.competition) == ("Arsenal", "Chelsea", "E0")


def test_store_is_idempotent_for_same_taken_at(db):
    seed_aliases(db)
    store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    report = store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    assert report.snapshots == 0 and db.query(OddsSnapshot).count() == 3


def test_second_reading_adds_new_snapshots(db):
    seed_aliases(db)
    store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc))
    assert db.query(OddsSnapshot).count() == 6
