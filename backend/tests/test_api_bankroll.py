from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.models.enums import MatchStatus
from app.models.team import Team
from tests.conftest import auth_header, make_match

NOW = datetime.now(timezone.utc)


def teams(db):
    seed_aliases(db)
    return db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()


def test_create_list_and_settle(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    r = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 1.9, "stake": 10}, headers=auth_header(starter_user))
    assert r.status_code == 201, r.text
    lst = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]
    assert lst["summary"]["pending"] == 1 and lst["summary"]["stakes"] == 10
    m.status, m.home_score, m.away_score = MatchStatus.FINISHED, 2, 0
    db.commit()
    lst = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]
    it = lst["items"][0]
    assert it["status"] == "WON" and it["payout"] == 19.0
    assert lst["summary"]["profit"] == 9.0 and lst["summary"]["roi"] == 0.9 and lst["summary"]["by_bookmaker"]["betclic_fr"]["profit"] == 9.0


def test_bankroll_timestamps_are_utc_aware_iso(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    r = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 1.9, "stake": 10}, headers=auth_header(starter_user))
    it = r.json()["data"]
    assert it["kickoff_at"].endswith("Z") or "+00:00" in it["kickoff_at"]
    assert it["created_at"].endswith("Z") or "+00:00" in it["created_at"]
    m.status = MatchStatus.POSTPONED; db.commit()
    voided = client.post(f"/api/v1/bankroll/{it['id']}/void", headers=auth_header(starter_user)).json()["data"]
    assert voided["settled_at"].endswith("Z") or "+00:00" in voided["settled_at"]


def test_lost_bet_and_delete_only_pending(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    bet_id = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "away", "bookmaker": "pmu_fr", "odds": 4.0, "stake": 5}, headers=auth_header(starter_user)).json()["data"]["id"]
    m.status, m.home_score, m.away_score = MatchStatus.FINISHED, 1, 0
    db.commit()
    assert client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]["items"][0]["status"] == "LOST"
    assert client.delete(f"/api/v1/bankroll/{bet_id}", headers=auth_header(starter_user)).status_code == 409


def test_void_only_when_postponed(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    bet_id = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "draw", "bookmaker": "winamax_fr", "odds": 3.5, "stake": 10}, headers=auth_header(starter_user)).json()["data"]["id"]
    before = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]["items"][0]
    assert before["match_status"] == "SCHEDULED"
    assert client.post(f"/api/v1/bankroll/{bet_id}/void", headers=auth_header(starter_user)).status_code == 409
    m.status = MatchStatus.POSTPONED; db.commit()
    r = client.post(f"/api/v1/bankroll/{bet_id}/void", headers=auth_header(starter_user))
    assert r.status_code == 200 and r.json()["data"]["status"] == "VOID" and r.json()["data"]["payout"] == 10
    after = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]["items"][0]
    assert after["match_status"] == "POSTPONED"


def test_validation_and_isolation(client, db, starter_user, pro_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    bad = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 0.9, "stake": 10}, headers=auth_header(starter_user))
    assert bad.status_code == 422
    client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 1.9, "stake": 10}, headers=auth_header(starter_user))
    assert client.get("/api/v1/bankroll", headers=auth_header(pro_user)).json()["data"]["items"] == []
    assert client.get("/api/v1/bankroll").status_code == 401


def test_pending_bet_has_no_profit_yet(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "home", "bookmaker": "betclic_fr", "odds": 1.9, "stake": 10}, headers=auth_header(starter_user))
    summary = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]["summary"]
    assert summary["stakes"] == 10
    assert summary["settled_stakes"] == 0
    assert summary["profit"] == 0.0
    assert summary["roi"] is None
    assert summary["pending"] == 1


def test_void_bet_is_neutral(client, db, starter_user):
    h, a = teams(db)
    m = make_match(db, h, a, kickoff=NOW + timedelta(days=1))
    bet_id = client.post("/api/v1/bankroll", json={"match_id": str(m.id), "outcome": "draw", "bookmaker": "winamax_fr", "odds": 3.5, "stake": 10}, headers=auth_header(starter_user)).json()["data"]["id"]
    m.status = MatchStatus.POSTPONED
    db.commit()
    client.post(f"/api/v1/bankroll/{bet_id}/void", headers=auth_header(starter_user))
    summary = client.get("/api/v1/bankroll", headers=auth_header(starter_user)).json()["data"]["summary"]
    assert summary["profit"] == 0.0
    assert summary["roi"] is None
    assert summary["stakes"] == 10
    assert summary["settled_stakes"] == 0
