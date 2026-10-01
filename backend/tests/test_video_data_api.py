"""`GET /api/v1/internal/video-data` : le JSON de `python -m app.tools.video_data`, derrière un jeton.

Tout échec d'authentification répond comme une route inconnue (404, même corps) : la route ne se
révèle qu'à qui présente le bon jeton — même un 422 de paramètres ne sort qu'après le jeton.
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from app.core.client_ip import limiter
from app.core.config import settings
from app.main import create_app
from app.models.enums import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.tools import video_data
from tests.conftest import make_match, make_team

URL = "/api/v1/internal/video-data"
JETON = "jeton-de-test-long-et-aleatoire-0123456789-abcdef"
KICK = datetime(2026, 10, 10, 18, 45, tzinfo=timezone.utc)
FIGE = datetime(2026, 10, 9, 6, 30, 12, 345, tzinfo=timezone.utc)
FENETRES = {"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-11",
            "termines_du": "2026-10-10", "termines_au": "2026-10-10"}
INTROUVABLE = {"success": False, "message": "Not Found", "data": None}


@pytest.fixture(autouse=True)
def _compteurs_a_zero():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def jeton(monkeypatch):
    monkeypatch.setattr(settings, "video_data_token", JETON)
    return JETON


def get(client, params=None, token=None, ip="198.51.100.20"):
    headers = {"X-Forwarded-For": ip}
    if token is not None:
        headers["X-Video-Token"] = token
    return client.get(URL, params=params, headers=headers)


@pytest.fixture
def donnees(db):
    """Un match à venir (E0), un terminé (F1), et un N1 hors de la liste par défaut."""
    h, a = make_team(db, "Saint-Étienne"), make_team(db, "Nîmes Olympique")

    def cotes(m, odds, t, book="pinnacle"):
        db.add(OddsSnapshot(match_id=m.id, bookmaker=book, taken_at=t, home=odds[0], draw=odds[1], away=odds[2]))
        db.commit()

    m = make_match(db, h, a, kickoff=KICK)
    cotes(m, (2.1, 3.3, 3.6), KICK - timedelta(days=1))
    cotes(m, (2.05, 3.4, 3.7), KICK - timedelta(days=1), book="betclic_fr")
    f = make_match(db, a, h, kickoff=KICK, competition="F1", status=MatchStatus.FINISHED, home_score=0, away_score=3)
    cotes(f, (1.8, 3.6, 4.5), KICK - timedelta(hours=2))
    n = make_match(db, h, a, kickoff=KICK, competition="N1")
    cotes(n, (1.5, 4.2, 6.5), KICK - timedelta(days=1))


# --- la route n'existe pas pour qui n'a pas le jeton --------------------------------------------------------------

def test_404_sans_reglage_meme_avec_un_en_tete(client, monkeypatch):
    monkeypatch.setattr(settings, "video_data_token", "")
    r = get(client, FENETRES, token="")
    assert r.status_code == 404 and r.json() == INTROUVABLE
    assert get(client, FENETRES, token="n-importe-quoi").json() == INTROUVABLE


def test_404_si_le_reglage_est_trop_court(client, monkeypatch):
    monkeypatch.setattr(settings, "video_data_token", "court")      # fermé plutôt que devinable
    assert get(client, FENETRES, token="court").status_code == 404


def test_404_sans_en_tete(client, jeton):
    r = get(client, FENETRES)
    assert r.status_code == 404 and r.json() == INTROUVABLE
    assert r.json() == client.get("/api/v1/nexistepas").json()       # indiscernable d'une route inconnue


@pytest.mark.parametrize("faux", ["", "mauvais", JETON[:-1], JETON + "x", JETON.upper(), "é".encode("latin-1") + JETON[1:].encode()])   # octet non ASCII : pas de TypeError côté serveur
def test_404_mauvais_jeton(client, jeton, faux):
    r = get(client, FENETRES, token=faux)
    assert r.status_code == 404 and r.json() == INTROUVABLE


def test_parametres_invalides_sans_jeton_restent_404(client, jeton):
    """Un 422 avant le jeton dirait « cette route existe »."""
    assert get(client, {"a_venir_du": "pas-une-date"}).status_code == 404
    assert get(client, {"a_venir_du": "pas-une-date"}, token="mauvais").status_code == 404


def test_absente_de_l_openapi(client):
    chemins = client.get("/openapi.json").json()["paths"]            # docs ouvertes hors production
    assert "/api/v1/matches" in chemins
    assert not [c for c in chemins if "internal" in c]


def test_openapi_ferme_en_production(monkeypatch):
    monkeypatch.setattr(settings, "env", "production")
    assert create_app().openapi_url is None


# --- le bon jeton : exactement le JSON de la commande ------------------------------------------------------------

def test_200_bon_jeton_json_identique_a_la_commande(client, db, jeton, donnees, monkeypatch, capsysbinary):
    class Fige(datetime):
        @classmethod
        def now(cls, tz=None):
            return FIGE
    monkeypatch.setattr(video_data, "datetime", Fige)

    ecritures = []
    def espion(conn, cursor, statement, *args):
        if statement.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            ecritures.append(statement)
    event.listen(db.get_bind(), "before_cursor_execute", espion)
    try:
        r = get(client, FENETRES, token=JETON)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", espion)

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert "Saint-Étienne".encode("utf-8") in r.content                  # UTF-8, pas d'échappement É
    assert ecritures == []                                                # lecture seule
    data = r.json()
    assert list(data) == ["version", "genere_le", "a_venir", "lus_par_jour", "termines"]  # pas d'enveloppe {success, data}
    assert data["genere_le"] == "2026-10-09T06:30:12Z"
    assert [i["competition"] for i in data["a_venir"]] == ["E0"]          # N1 exclu par défaut, comme la commande
    assert [i["competition"] for i in data["termines"]] == ["F1"]

    attendu = video_data.build(db, a_venir_du=date(2026, 10, 10), a_venir_au=date(2026, 10, 11),
                               termines_du=date(2026, 10, 10), termines_au=date(2026, 10, 10))
    assert data == attendu

    video_data.main(["--a-venir-du", "2026-10-10", "--a-venir-au", "2026-10-11",
                     "--termines-du", "2026-10-10", "--termines-au", "2026-10-10"], session_factory=lambda: db)
    assert data == json.loads(capsysbinary.readouterr().out.decode("utf-8"))


def test_une_seule_fenetre_et_filtre_de_competitions(client, jeton, donnees):
    r = get(client, {"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-10", "competitions": "n1, e0"}, token=JETON)
    assert r.status_code == 200
    data = r.json()
    assert sorted(i["competition"] for i in data["a_venir"]) == ["E0", "N1"] and data["termines"] == []


def test_le_jeton_n_est_jamais_journalise(client, jeton, donnees, caplog):
    with caplog.at_level(logging.DEBUG):
        get(client, FENETRES, token=JETON)
        get(client, FENETRES, token=JETON + "faux")
    assert JETON not in caplog.text


# --- paramètres : mêmes règles que la commande, 422 dans l'enveloppe ----------------------------------------------

@pytest.mark.parametrize("params, fragment", [
    ({}, "rien à produire"),
    ({"a_venir_du": "2026-10-10"}, "vont ensemble"),
    ({"a_venir_du": "2026-10-12", "a_venir_au": "2026-10-10"}, "est après"),
    ({"termines_du": "10/10/2026", "termines_au": "2026-10-10"}, "AAAA-MM-JJ"),
    ({"termines_du": "", "termines_au": "2026-10-10"}, "AAAA-MM-JJ"),
    ({"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-10", "competitions": "XX"}, "compétition inconnue"),
    ({"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-10", "competitions": ""}, "compétition inconnue"),
    ({"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-10", "sortie": "/tmp/x.json"}, "paramètre inconnu"),
])
def test_parametres_invalides_422_enveloppe(client, jeton, params, fragment):
    r = get(client, params, token=JETON)
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False and body["data"] is None
    assert fragment in body["message"]


# --- limites de débit ------------------------------------------------------------------------------------------------

def test_limite_de_debit_par_adresse(client, jeton):
    codes = [get(client, {"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-10"}, token=JETON).status_code
             for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429
    autre = get(client, {"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-10"}, token=JETON, ip="198.51.100.21")
    assert autre.status_code == 200                                       # compteur par adresse


def test_essais_rates_ferment_l_adresse_meme_au_bon_jeton(client, jeton):
    """Au-delà de 10 faux jetons par heure, l'adresse ne voit plus que des 404 : l'essai systématique
    ne peut plus distinguer le bon jeton."""
    params = {"a_venir_du": "2026-10-10", "a_venir_au": "2026-10-10"}
    assert [get(client, params, token=f"faux-{i}").status_code for i in range(10)] == [404] * 10
    r = get(client, params, token=JETON)
    assert r.status_code == 404 and r.json() == INTROUVABLE
    assert get(client, params, token=JETON, ip="198.51.100.22").status_code == 200
