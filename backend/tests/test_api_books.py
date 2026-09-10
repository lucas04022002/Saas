from datetime import datetime, timedelta, timezone

from app.models.odds_snapshot import OddsSnapshot
from tests.conftest import auth_header
from tests.test_api_matches import seed_match_with_odds

NOW = datetime.now(timezone.utc)


def test_books_requires_pro(client, db, starter_user):
    seed_match_with_odds(db)
    assert client.get("/api/v1/books").status_code == 403
    assert client.get("/api/v1/books", headers=auth_header(starter_user)).status_code == 403


def test_books_compare_french_bookmakers(client, db, pro_user):
    m = seed_match_with_odds(db)
    items = client.get("/api/v1/books", headers=auth_header(pro_user)).json()["data"]["items"]
    by = {i["bookmaker"]: i for i in items}
    assert set(by) == {"betclic_fr", "winamax_fr"}
    assert by["winamax_fr"]["matches"] == 1 and by["winamax_fr"]["best"]["match_id"] == str(m.id)
    assert by["winamax_fr"]["best"]["gap"] > by["betclic_fr"]["best"]["gap"]
    assert 0 < by["betclic_fr"]["avg_margin"] < 0.15
