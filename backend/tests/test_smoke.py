def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_signup_and_me(client):
    r = client.post("/api/v1/auth/signup", json={"first_name": "Lucas", "email": "lucas@test.fr", "password": "motdepasse123", "birth_date": "2000-01-01"})
    assert r.status_code in (200, 201), r.text
    token = r.json()["data"]["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["data"]["email"] == "lucas@test.fr"


def test_signup_refuses_minors(client):
    r = client.post("/api/v1/auth/signup", json={"first_name": "Jeune", "email": "j@test.fr", "password": "motdepasse123", "birth_date": "2015-01-01"})
    assert r.status_code == 422 and "18 ans" in r.text
