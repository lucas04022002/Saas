"""L'adresse du client derrière le proxy (audit du 22/09/2026, C2 — second passage).

Le premier correctif (`--proxy-headers` sur uvicorn) n'a pas suffi : test à deux adresses le
22/09 à 14:2x UTC, Lucas a reçu « Trop de tentatives » pendant que la mienne était bloquée. Le
limiteur voyait toujours une seule adresse pour tout le monde.

Deux garanties, indépendantes d'uvicorn :
- `client_ip` lit la première adresse de `X-Forwarded-For` (Traefik écrase cet en-tête par la vraie
  adresse : mesuré, 16 valeurs inventées n'ont pas contourné le 429), sinon `request.client.host` ;
- `/api/v1/whoami` rend cette adresse : la seule preuve directe de ce que l'API voit.
"""
from app.core.client_ip import client_ip


class _Req:
    def __init__(self, headers=None, host="10.0.0.9"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": host})()


def test_premiere_adresse_de_x_forwarded_for():
    assert client_ip(_Req({"x-forwarded-for": "203.0.113.7, 10.0.0.2"})) == "203.0.113.7"


def test_sans_en_tete_l_adresse_de_connexion():
    assert client_ip(_Req()) == "10.0.0.9"


def test_en_tete_vide_ou_blanc_retombe_sur_la_connexion():
    assert client_ip(_Req({"x-forwarded-for": "  "})) == "10.0.0.9"


def test_whoami_rend_l_adresse_vue(client):
    r = client.get("/api/v1/whoami", headers={"X-Forwarded-For": "198.51.100.4"})
    assert r.status_code == 200
    assert r.json()["data"]["ip"] == "198.51.100.4"


def test_le_limiteur_distingue_deux_adresses(client):
    """Onze tentatives par adresse : chacune a son propre compteur."""
    corps = {"email": "audit-inexistant@rushplay.fr", "password": "mauvais-mot-de-passe-123"}
    codes_a = [client.post("/api/v1/auth/login", json=corps, headers={"X-Forwarded-For": "198.51.100.1"}).status_code for _ in range(11)]
    codes_b = [client.post("/api/v1/auth/login", json=corps, headers={"X-Forwarded-For": "198.51.100.2"}).status_code for _ in range(11)]
    assert codes_a[:10] == [401] * 10 and codes_a[10] == 429
    assert codes_b[:10] == [401] * 10 and codes_b[10] == 429   # l'adresse B n'a pas hérité du compteur de A
