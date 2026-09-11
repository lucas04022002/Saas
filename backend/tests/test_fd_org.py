import json
import time
from datetime import date, datetime, timedelta, timezone
from datetime import time as fd_time
from pathlib import Path

from app.collectors import fd_org
from app.collectors.aliases import normalize, seed_aliases
from app.collectors.competitions import COMPETITIONS
from app.collectors.fd_org import FdOrgMatch, import_matches, parse_matches
from app.collectors.fd_uk import FixtureRow, import_fixtures
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


def test_import_reuses_match_created_by_fd_uk_fixtures_no_duplicate(db):
    """Chemin (a) du dédoublonnage : une ligne fixtures fd_uk existe déjà (fd_uk_key posé) ; fd_org importe le
    même match 1h plus tôt -> pas de nouvelle ligne, external_id attaché, kickoff pris depuis fd_org (autorité)."""
    seed_aliases(db)
    fixture_row = FixtureRow(div="E0", date=date(2026, 9, 13), time=fd_time(17, 0), home="Arsenal", away="Chelsea", avg=(1.9, 3.5, 4.0), max_=None)
    import_fixtures(db, [fixture_row], datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))
    existing = db.query(Match).filter(Match.home_team == "Arsenal").one()
    assert existing.fd_uk_key is not None and existing.external_id is None
    kickoff_fd_uk = existing.kickoff_at.replace(tzinfo=timezone.utc)

    item = FdOrgMatch(ext_id="fdo:900", competition_code="E0", utc_date=kickoff_fd_uk - timedelta(hours=1),
                       home="Arsenal FC", away="Chelsea FC", status="TIMED", hg=None, ag=None)
    report = import_matches(db, [item])

    assert report.created == 0 and report.updated == 1
    assert db.query(Match).count() == 1
    db.refresh(existing)
    assert existing.external_id == "fdo:900"
    assert existing.kickoff_at.replace(tzinfo=timezone.utc) == kickoff_fd_uk - timedelta(hours=1)
    assert existing.fd_uk_key is not None   # les deux identifiants cohabitent sur la même ligne


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


def test_quarantine_recovery_merges_into_match_already_resolved_by_another_source(db):
    """Reproduit le bug réel observé en prod : la quarantaine fd_org ne peut pas être résolue par simple update
    quand un match a déjà été créé pour les mêmes équipes/le même jour par une autre source (odds_api, fd_uk) —
    l'update entrerait en conflit avec la contrainte d'unicité (compétition, kickoff, équipes). Il faut fusionner."""
    seed_aliases(db)
    tottenham = db.query(Team).filter_by(name="Tottenham").one()
    everton = db.query(Team).filter_by(name="Everton").one()
    resolved = make_match(db, tottenham, everton, competition="E0", kickoff=datetime(2026, 9, 13, 17, 30, tzinfo=timezone.utc))

    item = next(i for i in parse_matches(PAYLOAD) if i.home == "FC Nulle Part")   # id 537004, Everton en extérieur
    report = import_matches(db, [item])
    assert report.quarantined == 1
    assert db.query(Match).count() == 2   # la quarantaine + le match déjà résolu ailleurs

    db.add(TeamAlias(source="fd_org", alias=normalize("FC Nulle Part"), team_id=tottenham.id))
    db.commit()

    report2 = import_matches(db, [item])

    assert report2.quarantined == 0 and report2.updated == 1
    assert db.query(Match).filter(Match.status == MatchStatus.QUARANTINE).count() == 0
    assert db.query(Match).count() == 1
    survivor = db.query(Match).one()
    assert survivor.id == resolved.id
    assert survivor.external_id == "fdo:537004"
    assert survivor.status == MatchStatus.SCHEDULED


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


def test_run_skips_competitions_without_a_free_fd_org_calendar(db, monkeypatch):
    """EL (fd_org_free=False, plan payant chez football-data.org) ne doit jamais être appelée par fd_org.run."""
    calls = []

    def fake_fetch(code, date_from, date_to):
        calls.append(code)
        return {"competition": {"code": COMPETITIONS[code].fd_org_code}, "matches": []}

    monkeypatch.setattr(fd_org, "fetch", fake_fetch)
    monkeypatch.setattr(time, "sleep", lambda *_: None)

    fd_org.run(db)

    assert "EL" not in calls
    assert set(calls) == {c for c, comp in COMPETITIONS.items() if comp.fd_org_free}
