import json
from datetime import date, datetime, timezone
from datetime import time as fd_time
from pathlib import Path

from sqlalchemy.exc import IntegrityError

import app.collectors.odds_api as odds_api
from app.collectors.aliases import normalize, seed_aliases
from app.collectors.fd_uk import FixtureRow, import_fixtures
from app.collectors.odds_api import parse_events, parse_totals, store_events, store_totals
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team, TeamAlias
from app.models.totals_snapshot import TotalsSnapshot
from tests.conftest import make_match

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "odds_api_epl.json").read_text(encoding="utf-8"))
TOTALS_PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "odds_api_totals_epl.json").read_text(encoding="utf-8"))
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


def test_store_reuses_match_already_present_via_fd_uk_no_duplicate(db):
    """Chemin (c) du dédoublonnage : une ligne fixtures fd_uk existe déjà pour Arsenal-Chelsea ; l'événement
    odds_api pour le même match (même jour, quelques heures d'écart) ne doit pas créer de second match."""
    seed_aliases(db)
    fixture_row = FixtureRow(div="E0", date=date(2026, 9, 12), time=fd_time(15, 0), home="Arsenal", away="Chelsea", avg=(1.9, 3.5, 4.0), max_=None)
    import_fixtures(db, [fixture_row], datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))
    existing = db.query(Match).filter(Match.home_team == "Arsenal").one()
    assert existing.fd_uk_key is not None
    kickoff_before = existing.kickoff_at

    report = store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)   # commence_time 2026-09-12T14:00:00Z

    assert report.matched == 1
    assert db.query(Match).count() == 1
    db.refresh(existing)
    assert existing.fd_uk_key is not None   # toujours présent, jamais écrasé par odds_api
    assert existing.kickoff_at == kickoff_before   # odds_api ne réécrit jamais le coup d'envoi (seul fd_org le fait)
    snaps = db.query(OddsSnapshot).filter_by(match_id=existing.id).all()
    assert {s.bookmaker for s in snaps} == {"fd_uk_avg", "betclic_fr", "winamax_fr", "pinnacle"}


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


def test_unique_conflict_skips_event_and_keeps_session_usable(db, monkeypatch):
    seed_aliases(db)
    # rend le second événement (équipe fictive du fixture) résoluble pour qu'il atteigne aussi _find_or_create_match
    fcnp = Team(name="FC Nulle Part", country="Angleterre")
    db.add(fcnp); db.flush()
    db.add(TeamAlias(source="odds_api", alias=normalize("FC Nulle Part"), team_id=fcnp.id))
    db.commit()

    calls = {"n": 0}
    original = odds_api._find_or_create_match

    def flaky(db_, ev, home, away):
        calls["n"] += 1
        if calls["n"] == 1:
            raise IntegrityError("x", {}, Exception("dup"))
        return original(db_, ev, home, away)

    monkeypatch.setattr(odds_api, "_find_or_create_match", flaky)

    report = store_events(db, parse_events("soccer_epl", PAYLOAD), taken_at=T0)

    assert report.matched == 1
    assert db.query(Match).count() == 1   # la session reste utilisable après le rollback du premier événement


# --- totals (over/under) : total de buts attendu du marché, cf. app.engine.score.expected_total ---

def test_parse_totals_keeps_pinnacle_only_and_all_lines():
    ev = parse_totals("soccer_epl", TOTALS_PAYLOAD)[0]
    assert (ev.home, ev.away) == ("Arsenal", "Chelsea")
    assert set(ev.lines) == {2.5, 3.5}          # betclic_fr écarté, seul pinnacle est gardé
    assert ev.lines[2.5] == (1.85, 2.05)
    assert ev.lines[3.5] == (1.70, 2.25)


def test_parse_totals_tolerates_missing_totals_market():
    """Le second événement du fixture n'a qu'un marché h2h chez pinnacle, pas de marché totals : ignoré sans erreur."""
    events = parse_totals("soccer_epl", TOTALS_PAYLOAD)
    assert len(events) == 1   # seul Arsenal-Chelsea a un marché totals


def test_store_totals_reuses_match_resolved_by_h2h_pass(db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    m = make_match(db, h, a, kickoff=datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc))
    h2h_report = store_events(db, parse_events("soccer_epl", PAYLOAD), taken_at=T0)

    report = store_totals(db, parse_totals("soccer_epl", TOTALS_PAYLOAD), taken_at=T0, event_matches=h2h_report.event_matches)

    assert report.matched == 1 and report.totals == 2
    snaps = db.query(TotalsSnapshot).filter_by(match_id=m.id).all()
    assert {(s.line, s.over, s.under) for s in snaps} == {(2.5, 1.85, 2.05), (3.5, 1.70, 2.25)}
    assert all(s.bookmaker == "pinnacle" for s in snaps)


def test_store_totals_resolves_match_itself_when_no_h2h_pass(db):
    """Sans dict `event_matches` (ou l'événement absent du relevé h2h), store_totals résout le match lui-même,
    comme store_events."""
    seed_aliases(db)
    report = store_totals(db, parse_totals("soccer_epl", TOTALS_PAYLOAD), taken_at=T0)
    assert report.matched == 1 and report.totals == 2
    m = db.query(Match).filter(Match.home_team == "Arsenal", Match.away_team == "Chelsea").one()
    assert db.query(TotalsSnapshot).filter_by(match_id=m.id).count() == 2


def test_store_totals_is_idempotent_for_same_taken_at(db):
    seed_aliases(db)
    events = parse_totals("soccer_epl", TOTALS_PAYLOAD)
    store_totals(db, events, taken_at=T0)
    report = store_totals(db, events, taken_at=T0)
    assert report.totals == 0 and db.query(TotalsSnapshot).count() == 2


def test_store_totals_reports_zero_when_market_missing(db):
    """Événement sans marché totals (parse_totals ne le renvoie pas) : store_totals sur une liste vide ne crashe pas."""
    seed_aliases(db)
    report = store_totals(db, [], taken_at=T0)
    assert (report.matched, report.totals, report.quarantined) == (0, 0, 0)
