from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.collectors.aliases import seed_aliases
from app.engine.score import LEAGUE_GOALS
from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from app.models.totals_snapshot import TotalsSnapshot
from app.services.market_reading import reading_for
from tests.conftest import auth_header, make_match

NOW = datetime.now(timezone.utc)
PARIS = ZoneInfo("Europe/Paris")


def paris_day(dt: datetime) -> str:
    """Date (YYYY-MM-DD) du jour Paris correspondant à un kickoff UTC — utilisé pour interroger ?date=,
    qui est désormais interprété par le backend comme un jour Paris (00:00-24:00 Paris converti en bornes UTC)."""
    return dt.astimezone(PARIS).date().isoformat()


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
    # score le plus probable : public, non verrouillé même pour l'anonyme
    assert it["top_score"]["score"].count("-") == 1
    i, j = (int(x) for x in it["top_score"]["score"].split("-"))
    assert i > j    # favori domicile -> score de victoire domicile
    assert 0 < it["top_score"]["probability"] < 1


def test_list_shows_gap_and_movement_for_pro(client, db, pro_user):
    seed_match_with_odds(db)
    it = client.get("/api/v1/matches", headers=auth_header(pro_user)).json()["data"]["items"][0]
    assert it["locked"] is False
    assert it["best_gap"]["bookmaker"] == "winamax_fr" and it["best_gap"]["outcome"] == "home" and it["best_gap"]["gap"] > 0
    assert it["movement"]["home"] != 0


def test_list_filters_by_date_and_competition(client, db):
    m = seed_match_with_odds(db)
    day = paris_day(m.kickoff_at)
    assert len(client.get(f"/api/v1/matches?date={day}").json()["data"]["items"]) == 1
    assert client.get(f"/api/v1/matches?date={day}&competition=F1").json()["data"]["items"] == []


def test_list_date_filter_uses_paris_day_not_utc_day(client, db):
    """22:30 UTC le 11/09 = 00:30 CEST le 12/09 (Paris, UTC+2 l'été) : le match doit apparaître sous date=2026-09-12,
    pas sous date=2026-09-11, même si son kickoff_at UTC porte le 11."""
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    kickoff = datetime(2026, 9, 11, 22, 30, tzinfo=timezone.utc)
    m = make_match(db, h, a, kickoff=kickoff)
    db.add(OddsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=kickoff - timedelta(hours=3), home=2.0, draw=3.5, away=3.8))
    db.commit()
    assert client.get("/api/v1/matches?date=2026-09-12").json()["data"]["items"] != []
    assert client.get("/api/v1/matches?date=2026-09-11").json()["data"]["items"] == []


def test_matches_and_match_detail_timestamps_are_utc_aware_iso(client, db, pro_user):
    m = seed_match_with_odds(db)
    items = client.get("/api/v1/matches", headers=auth_header(pro_user)).json()["data"]["items"]
    it = items[0]
    assert it["kickoff_at"].endswith("Z") or "+00:00" in it["kickoff_at"]
    assert it["odds_taken_at"].endswith("Z") or "+00:00" in it["odds_taken_at"]
    detail = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert detail["kickoff_at"].endswith("Z") or "+00:00" in detail["kickoff_at"]
    for h in detail["history"]:
        assert h["taken_at"].endswith("Z") or "+00:00" in h["taken_at"]


def test_list_accepts_el_competition_filter(client, db):
    """EL (Ligue Europa, calendrier payant chez fd_org) doit être une valeur acceptée par le filtre, même sans match."""
    r = client.get("/api/v1/matches?competition=EL")
    assert r.status_code == 200
    assert r.json()["data"]["items"] == []


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
    assert "en tête" in d["analysis"]
    assert d["form"]["home"]["played"] == 0 and d["h2h"] == [] and d["result"] is None
    # score le plus probable (cohérent avec le favori) et distribution des 5 scores les plus probables (non
    # contrainte par le favori, donc peut différer du score en tête) : la distribution est réservée au pro
    i, j = (int(x) for x in d["top_score"]["score"].split("-"))
    assert i > j    # favori domicile
    assert len(d["score_distribution"]) == 5
    probs = [s["probability"] for s in d["score_distribution"]]
    assert probs == sorted(probs, reverse=True)


def test_detail_anonymous_is_locked_but_keeps_favourite_and_analysis(client, db):
    m = seed_match_with_odds(db)
    d = client.get(f"/api/v1/matches/{m.id}").json()["data"]
    assert d["locked"] is True and d["books"] is None and d["history"] is None and d["movement"] is None
    assert d["favourite"]["outcome"] == "home" and d["analysis"]
    assert "au-dessus de la référence" not in d["analysis"]
    assert "depuis le premier relevé" not in d["analysis"]
    # top_score public même verrouillé, score_distribution réservé au pro
    assert d["top_score"] is not None
    assert d["score_distribution"] is None


def test_detail_uses_finished_history_for_form_and_h2h(client, db, pro_user):
    m = seed_match_with_odds(db)
    h, a = m.home, m.away
    make_match(db, h, a, kickoff=NOW - timedelta(days=200), status=MatchStatus.FINISHED, home_score=2, away_score=0)
    make_match(db, a, h, kickoff=NOW - timedelta(days=30), status=MatchStatus.FINISHED, home_score=1, away_score=1)
    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert d["form"]["home"]["sequence"] == "NV" and d["form"]["away"]["sequence"] == "ND"
    assert [x["score"] for x in d["h2h"]] == ["1-1", "2-0"]


def test_detail_history_matches_movement(client, db, pro_user):
    m = seed_match_with_odds(db)
    r = reading_for(m)
    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert len(d["history"]) == 2
    assert datetime.fromisoformat(d["history"][0]["taken_at"]) == r.first_taken_at.replace(tzinfo=timezone.utc)
    assert d["odds_taken_at"] == d["history"][-1]["taken_at"]
    assert client.get("/api/v1/matches/00000000-0000-0000-0000-000000000000").status_code == 404
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Lyon").one(), db.query(Team).filter_by(name="Nice").one()
    q = make_match(db, h, a, competition="F1", status=MatchStatus.QUARANTINE)
    assert client.get(f"/api/v1/matches/{q.id}").status_code == 404


def test_detail_expected_goals_falls_back_to_league_without_totals_snapshot(client, db, pro_user):
    m = seed_match_with_odds(db)
    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert d["expected_goals"] == {"total": LEAGUE_GOALS["E0"], "source": "ligue"}


def test_detail_expected_goals_and_top_score_use_market_totals_snapshot(client, db, pro_user):
    """Une ligne over/under 2,5 fortement inclinée vers l'over doit faire basculer le score en tête (plus de
    buts que le repli de ligue), et la source affichée doit passer de « ligue » à « marché »."""
    m = seed_match_with_odds(db)
    without = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert without["expected_goals"]["source"] == "ligue"
    assert without["top_score"]["score"] == "1-0"

    db.add(TotalsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=NOW - timedelta(hours=3), line=2.5, over=1.30, under=3.55))
    db.commit()

    with_market = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert with_market["expected_goals"]["source"] == "marché"
    assert with_market["expected_goals"]["total"] > LEAGUE_GOALS["E0"]
    assert with_market["top_score"]["score"] == "2-1"
    assert with_market["top_score"]["score"] != without["top_score"]["score"]


def test_detail_expected_goals_picks_the_line_with_closest_over_under_odds_not_2_5(client, db, pro_user):
    """Pinnacle poste rarement la ligne 2,5 (mesuré : 19 relevés sur 131) — la ligne principale du relevé est
    celle où over et under sont les plus proches l'une de l'autre, pas forcément 2,5."""
    m = seed_match_with_odds(db)
    same_relevé = NOW - timedelta(hours=3)
    # 2,5 est très inclinée (pas la ligne principale) ; 2,75 est quasi équilibrée (la ligne principale)
    db.add(TotalsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=same_relevé, line=2.5, over=1.30, under=3.55))
    db.add(TotalsSnapshot(match_id=m.id, bookmaker="pinnacle", taken_at=same_relevé, line=2.75, over=1.92, under=1.92))
    db.commit()

    d = client.get(f"/api/v1/matches/{m.id}", headers=auth_header(pro_user)).json()["data"]
    assert d["expected_goals"]["source"] == "marché"
    assert d["expected_goals"]["total"] == pytest.approx(2.908, abs=1e-3)   # ligne 2,75, pas 2,5 (3,805)
