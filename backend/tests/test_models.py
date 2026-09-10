from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.odds_snapshot import OddsSnapshot
from app.models.team import TeamAlias
from tests.conftest import make_match, make_team


def test_snapshot_unique_per_match_bookmaker_time(db):
    h, a = make_team(db, "Arsenal"), make_team(db, "Chelsea")
    m = make_match(db, h, a)
    t = datetime(2026, 9, 12, 8, 0, tzinfo=timezone.utc)
    db.add(OddsSnapshot(match_id=m.id, bookmaker="betclic_fr", taken_at=t, home=1.9, draw=3.5, away=4.0)); db.commit()
    db.add(OddsSnapshot(match_id=m.id, bookmaker="betclic_fr", taken_at=t, home=1.95, draw=3.5, away=4.0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_alias_unique_per_source(db):
    h = make_team(db, "Manchester United")
    db.add(TeamAlias(source="fd_uk", alias="Man United", team_id=h.id)); db.commit()
    db.add(TeamAlias(source="fd_uk", alias="Man United", team_id=h.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_match_natural_key_unique(db):
    h, a = make_team(db, "Lyon"), make_team(db, "Marseille")
    make_match(db, h, a, competition="F1")
    with pytest.raises(IntegrityError):
        make_match(db, h, a, competition="F1")
    db.rollback()
