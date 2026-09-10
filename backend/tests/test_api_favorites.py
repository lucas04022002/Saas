from datetime import datetime, timezone

from app.collectors.aliases import seed_aliases
from app.models.team import Team
from tests.conftest import auth_header, make_match


def seed_match(db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    return make_match(db, h, a, kickoff=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc))


def test_add_list_and_delete_favorite(client, db, starter_user):
    m = seed_match(db)
    headers = auth_header(starter_user)

    r = client.post(f"/api/v1/favorites/{m.id}", headers=headers)
    assert r.status_code in (200, 201)

    items = client.get("/api/v1/favorites", headers=headers).json()["data"]
    assert len(items) == 1 and items[0]["match_id"] == str(m.id)

    r = client.delete(f"/api/v1/favorites/{m.id}", headers=headers)
    assert r.status_code == 200

    r = client.delete(f"/api/v1/favorites/{m.id}", headers=headers)
    assert r.status_code == 404


def test_add_favorite_twice_is_conflict(client, db, starter_user):
    m = seed_match(db)
    headers = auth_header(starter_user)
    client.post(f"/api/v1/favorites/{m.id}", headers=headers)
    r = client.post(f"/api/v1/favorites/{m.id}", headers=headers)
    assert r.status_code == 409


def test_malformed_match_id_is_404(client, db, starter_user):
    headers = auth_header(starter_user)
    assert client.post("/api/v1/favorites/not-a-uuid", headers=headers).status_code == 404
    assert client.delete("/api/v1/favorites/not-a-uuid", headers=headers).status_code == 404


def test_favorites_require_authentication(client, db):
    m = seed_match(db)
    assert client.get("/api/v1/favorites").status_code == 401
    assert client.post(f"/api/v1/favorites/{m.id}").status_code == 401
    assert client.delete(f"/api/v1/favorites/{m.id}").status_code == 401
