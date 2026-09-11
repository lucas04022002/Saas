from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.collectors.dedup import dedup_matches, find_existing, merge_matches
from app.models.bet import Bet
from app.models.enums import BetStatus, MatchStatus, Outcome
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import make_match, make_user

K0 = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)


def teams(db):
    seed_aliases(db)
    return db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()


# ---- find_existing ----

def test_find_existing_returns_match_within_window(db):
    h, a = teams(db)
    m = make_match(db, h, a, competition="E0", kickoff=K0)
    found = find_existing(db, "E0", h.id, a.id, K0 + timedelta(hours=1))
    assert found.id == m.id


def test_find_existing_ignores_matches_outside_window(db):
    h, a = teams(db)
    make_match(db, h, a, competition="E0", kickoff=K0)
    assert find_existing(db, "E0", h.id, a.id, K0 + timedelta(hours=37)) is None


def test_find_existing_ignores_quarantine_rows(db):
    h, a = teams(db)
    m = make_match(db, h, a, competition="E0", kickoff=K0, status=MatchStatus.QUARANTINE)
    assert find_existing(db, "E0", h.id, a.id, K0) is None
    assert m.status == MatchStatus.QUARANTINE   # sanity


def test_find_existing_returns_none_without_team_ids(db):
    assert find_existing(db, "E0", None, None, K0) is None


# ---- merge_matches ----

def test_merge_matches_moves_snapshots_bets_and_keys_then_deletes_duplicate(db):
    h, a = teams(db)
    keep = make_match(db, h, a, competition="E0", kickoff=K0)
    keep.fd_uk_key = "E0:2026-09-13:Arsenal:Chelsea"
    remove = make_match(db, h, a, competition="E0", kickoff=K0 + timedelta(hours=1))
    remove.external_id = "fdo:12345"
    db.add(OddsSnapshot(match_id=remove.id, bookmaker="pinnacle", taken_at=K0 - timedelta(hours=1), home=2.0, draw=3.4, away=3.6))
    user = make_user(db)
    bet = Bet(user_id=user.id, match_id=remove.id, outcome=Outcome.HOME, bookmaker="pinnacle", odds=2.0, stake=10)
    db.add(bet)
    db.commit()
    remove_id = remove.id

    merge_matches(db, keep, remove)
    db.commit()

    assert db.get(Match, remove_id) is None
    db.refresh(keep)
    assert keep.external_id == "fdo:12345" and keep.fd_uk_key == "E0:2026-09-13:Arsenal:Chelsea"
    snaps = db.query(OddsSnapshot).filter_by(match_id=keep.id).all()
    assert len(snaps) == 1 and snaps[0].bookmaker == "pinnacle"
    db.refresh(bet)
    assert bet.match_id == keep.id


def test_merge_matches_drops_conflicting_snapshot_instead_of_duplicating(db):
    h, a = teams(db)
    keep = make_match(db, h, a, competition="E0", kickoff=K0)
    remove = make_match(db, h, a, competition="E0", kickoff=K0 + timedelta(hours=1))
    t = K0 - timedelta(hours=1)
    db.add(OddsSnapshot(match_id=keep.id, bookmaker="pinnacle", taken_at=t, home=2.0, draw=3.4, away=3.6))
    db.add(OddsSnapshot(match_id=remove.id, bookmaker="pinnacle", taken_at=t, home=1.9, draw=3.5, away=3.8))   # même bookmaker/taken_at
    db.commit()

    merge_matches(db, keep, remove)
    db.commit()

    snaps = db.query(OddsSnapshot).filter_by(match_id=keep.id).all()
    assert len(snaps) == 1   # le relevé en conflit a été abandonné, pas dupliqué


# ---- dedup_matches ----

def test_dedup_two_duplicates_with_snapshots_on_both_keeps_one_survivor_with_all_snapshots(db):
    h, a = teams(db)
    m1 = make_match(db, h, a, competition="E0", kickoff=K0)
    m1.external_id = "fdo:1"
    m2 = make_match(db, h, a, competition="E0", kickoff=K0 + timedelta(hours=1))
    db.add(OddsSnapshot(match_id=m1.id, bookmaker="pinnacle", taken_at=K0 - timedelta(hours=2), home=2.0, draw=3.4, away=3.6))
    db.add(OddsSnapshot(match_id=m2.id, bookmaker="betclic_fr", taken_at=K0 - timedelta(hours=1), home=1.9, draw=3.5, away=3.8))
    db.commit()

    report = dedup_matches(db)

    assert report.groups == 1 and report.removed == 1
    assert db.query(Match).filter(Match.competition == "E0").count() == 1
    survivor = db.query(Match).filter(Match.competition == "E0").one()
    assert survivor.external_id == "fdo:1"
    assert {s.bookmaker for s in db.query(OddsSnapshot).filter_by(match_id=survivor.id).all()} == {"pinnacle", "betclic_fr"}


def test_dedup_quarantine_plus_resolved_row_quarantine_removed(db):
    """Une ligne QUARANTINE dont les équipes ont malgré tout été assignées (recovery partielle) et une ligne
    résolue pour le même match : dedup_matches les fusionne, la ligne QUARANTINE disparaît."""
    h, a = teams(db)
    resolved = make_match(db, h, a, competition="E0", kickoff=K0)
    quarantine = make_match(db, h, a, competition="E0", kickoff=K0 + timedelta(hours=1), status=MatchStatus.QUARANTINE)
    db.commit()

    report = dedup_matches(db)

    assert report.groups == 1 and report.removed == 1
    assert db.query(Match).filter(Match.competition == "E0").count() == 1
    assert db.query(Match).filter(Match.id == quarantine.id).count() == 0
    survivor = db.query(Match).filter(Match.competition == "E0").one()
    assert survivor.id == resolved.id and survivor.status == MatchStatus.SCHEDULED


def test_dedup_matches_3_days_apart_are_not_merged(db):
    h, a = teams(db)
    make_match(db, h, a, competition="E0", kickoff=K0)
    make_match(db, h, a, competition="E0", kickoff=K0 + timedelta(days=3))
    db.commit()

    report = dedup_matches(db)

    assert report.groups == 0 and report.removed == 0
    assert db.query(Match).filter(Match.competition == "E0").count() == 2
