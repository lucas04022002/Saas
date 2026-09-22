"""En-têtes de sécurité de l'API et documentation en production (audit du 22/09/2026)."""
from fastapi.testclient import TestClient

from app import main
from app.core.config import settings


def test_les_reponses_de_l_api_portent_les_en_tetes_de_securite(client):
    h = client.get("/health").headers
    assert h.get("strict-transport-security", "").startswith("max-age=")
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("x-frame-options") == "DENY"
    assert h.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "cache-control" in h   # les réponses JSON personnalisées ne doivent pas être mises en cache par un proxy


def test_swagger_est_ferme_en_production(monkeypatch):
    """`api.rushplay.fr/docs` répondait 200 : toute la surface documentée, webhook compris."""
    monkeypatch.setattr(settings, "env", "production")
    app = main.create_app()
    with TestClient(app) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404


def test_swagger_reste_ouvert_en_developpement(monkeypatch):
    monkeypatch.setattr(settings, "env", "development")
    app = main.create_app()
    with TestClient(app) as c:
        assert c.get("/openapi.json").status_code == 200
