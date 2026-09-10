from datetime import datetime, timedelta, timezone

from app.collectors.aliases import seed_aliases
from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import auth_header, make_match

NOW = datetime.now(timezone.utc)


def seed_match_with_odds(db, kickoff=None):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    m = make_match(db, h, a, kickoff=kickoff or NOW + timedelta(days=2))
    t0, t1 = NOW - timedelta(days=2), NOW - timedelta(hours=3)
    for book, t, odds in [("pinnacle", t0, (2.10, 3.6, 3.8)), ("betclic_fr", t0, (2.0, 3.5, 3.7)),
                          ("pinnacle", t1, (1.95, 3.7, 4.1)), ("betclic_fr", t1, (1.9, 3.55, 3.9)), ("winamax_fr", t1, (2.05, 3.5, 3.8))]:
        db.add(OddsSnapshot(match_id=m.id, bookmaker=book, taken_at=t, home=odds[0], draw=odds[1], away=odds[2]))
    db.commit()
    return m


def test_list_upcoming_shows_favourite_and_locks_premium_for_anonymous(client, db):
    seed_match_with_odds(db)
    r = client.get("/api/v1/matches")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 1
    it = items[0]
    assert it["favourite"]["outcome"] == "home" and it["favourite"]["label"] == "Arsenal" and it["favourite"]["source"] == "pinnacle"
    assert it["locked"] is True and it["best_gap"] is None and it["movement"] is None


def test_list_shows_gap_and_movement_for_pro(client, db, pro_user):
    seed_match_with_odds(db)
    it = client.get("/api/v1/matches", headers=auth_header(pro_user)).json()["data"]["items"][0]
    assert it["locked"] is False
    assert it["best_gap"]["bookmaker"] == "winamax_fr" and it["best_gap"]["outcome"] == "home" and it["best_gap"]["gap"] > 0
    assert it["movement"]["home"] != 0


def test_list_filters_by_date_and_competition(client, db):
    m = seed_match_with_odds(db)
    day = m.kickoff_at.date().isoformat()
    assert len(client.get(f"/api/v1/matches?date={day}").json()["data"]["items"]) == 1
    assert client.get(f"/api/v1/matches?date={day}&competition=F1").json()["data"]["items"] == []


def test_list_never_returns_quarantine_or_matches_without_odds(client, db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Lyon").one(), db.query(Team).filter_by(name="Nice").one()
    make_match(db, h, a, competition="F1", kickoff=NOW + timedelta(days=1))                    # sans relevé
    make_match(db, h, a, competition="F1", kickoff=NOW + timedelta(days=3), status=MatchStatus.QUARANTINE)
    items = client.get("/api/v1/matches").json()["data"]["items"]
    assert len(items) == 1 and items[0]["favourite"] is None and items[0]["odds_taken_at"] is None


def test_detail_pro_has_books_history_analysis(client, db, pro_user):
    m = seed_match_with_odds(db)
    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert {b["bookmaker"] for b in d["books"]} == {"betclic_fr", "winamax_fr"}
    assert d["reference_book"]["bookmaker"] == "pinnacle"
    assert len(d["history"]) == 2 and d["history"][0]["taken_at"] < d["history"][1]["taken_at"]
    assert d["analysis"].startswith("Arsenal est favori à")
    assert "depuis le premier relevé" in d["analysis"]
    assert d["form"]["home"]["played"] == 0 and d["h2h"] == [] and d["result"] is None


def test_detail_anonymous_is_locked_but_keeps_favourite_and_analysis(client, db):
    m = seed_match_with_odds(db)
    d = client.get(f"/api/v1/matches/{m.id}").json()["data"]
    assert d["locked"] is True and d["books"] is None and d["history"] is None and d["movement"] is None
    assert d["favourite"]["outcome"] == "home" and d["analysis"]
    assert "au-dessus de la référence" not in d["analysis"]
    assert "depuis le premier relevé" not in d["analysis"]


def test_detail_uses_finished_history_for_form_and_h2h(client, db, pro_user):
    m = seed_match_with_odds(db)
    h, a = m.home, m.away
    make_match(db, h, a, kickoff=NOW - timedelta(days=200), status=MatchStatus.FINISHED, home_score=2, away_score=0)
    make_match(db, a, h, kickoff=NOW - timedelta(days=30), status=MatchStatus.FINISHED, home_score=1, away_score=1)
    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert d["form"]["home"]["sequence"] == "NV" and d["form"]["away"]["sequence"] == "ND"
    assert [x["score"] for x in d["h2h"]] == ["1-1", "2-0"]


def test_detail_404_and_quarantine_hidden(client, db):
    assert client.get("/api/v1/matches/00000000-0000-0000-0000-000000000000").status_code == 404
