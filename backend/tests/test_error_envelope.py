"""Toutes les erreurs parlent l'enveloppe `{success, message, data}` (audit du 22/09/2026, F2).

Les 422 de validation sortaient dans la forme brute de FastAPI, expression régulière complète
comprise : le client devait connaître deux formats d'erreur."""


def test_une_erreur_de_validation_est_enveloppee(client):
    r = client.get("/api/v1/matches?competition=ZZ")
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False and body["data"] is None
    assert body["message"] and "pattern" not in body["message"].lower() or "competition" in body["message"]


def test_le_message_de_validation_reste_lisible(client):
    """La règle métier « 18 ans » doit toujours arriver telle quelle au formulaire."""
    r = client.post("/api/v1/auth/signup", json={"first_name": "Jeune", "email": "j@t.fr", "password": "motdepasse123", "birth_date": "2015-01-01"})
    assert r.status_code == 422
    assert "18 ans" in r.json()["message"]


def test_une_route_inconnue_est_enveloppee(client):
    r = client.get("/api/v1/nexistepas")
    assert r.status_code == 404
    assert r.json() == {"success": False, "message": "Not Found", "data": None}
