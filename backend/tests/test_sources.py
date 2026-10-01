"""Mesure des réseaux (01/10/2026) : `?ref=` → compteur de visites, source gardée à l'inscription, bilan."""
import io
import sys
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.client_ip import limiter
from app.core.sources import source_valide
from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.source_visit import SourceVisit
from app.models.subscription import Subscription
from app.models.user import User
from app.services.sources import bilan, compter_visite
from app.tools import sources as outil
from tests.conftest import make_user


@pytest.fixture(autouse=True)
def _limiteur_neuf():
    limiter.reset()
    yield
    limiter.reset()


def _inscription(client, email, **extra):
    return client.post("/api/v1/auth/signup", json={"first_name": "Lucas", "email": email, "password": "motdepasse123",
                                                    "birth_date": "2000-01-01", **extra})


def test_source_valide_liste_fermee():
    assert source_valide(" TikTok ") == "tiktok"
    assert source_valide("insta") == "insta"
    assert source_valide("LinkedIn") == "linkedin"
    assert source_valide("pirate") is None
    assert source_valide("") is None and source_valide(None) is None


def test_visite_comptee_par_jour_et_source(client, db):
    for _ in range(3):
        assert client.post("/api/v1/visits", json={"source": "tiktok"}).status_code == 200
    client.post("/api/v1/visits", json={"source": "insta"})
    rangs = {r.source: r.visits for r in db.scalars(select(SourceVisit))}
    assert rangs == {"tiktok": 3, "insta": 1}


def test_visite_source_inconnue_ignoree_sans_erreur(client, db):
    r = client.post("/api/v1/visits", json={"source": "pirate"})
    assert r.status_code == 200
    assert db.scalars(select(SourceVisit)).all() == []


def test_visite_limitee_par_adresse(client):
    codes = [client.post("/api/v1/visits", json={"source": "tiktok"}).status_code for _ in range(21)]
    assert codes[:20] == [200] * 20 and codes[20] == 429


def test_compteur_jours_separes(db):
    compter_visite(db, "tiktok", date(2026, 10, 1))
    compter_visite(db, "tiktok", date(2026, 10, 2))
    compter_visite(db, "tiktok", date(2026, 10, 2))
    assert sorted((r.day.isoformat(), r.visits) for r in db.scalars(select(SourceVisit))) == [
        ("2026-10-01", 1), ("2026-10-02", 2)]


def test_inscription_garde_la_source(client, db):
    assert _inscription(client, "a@test.fr", source="tiktok").status_code in (200, 201)
    assert _inscription(client, "b@test.fr", source="pirate").status_code in (200, 201)  # jamais un refus
    assert _inscription(client, "c@test.fr").status_code in (200, 201)
    src = {u.email: u.signup_source for u in db.scalars(select(User))}
    assert src == {"a@test.fr": "tiktok", "b@test.fr": None, "c@test.fr": None}


def test_bilan_visites_inscrits_abonnes(db):
    for _ in range(10):
        compter_visite(db, "tiktok")
    compter_visite(db, "insta")
    t1, t2 = make_user(db), make_user(db)
    paye = make_user(db, plan=SubscriptionPlan.PRO)
    for u in (t1, t2):
        u.signup_source = "tiktok"
    paye.signup_source = "tiktok"
    db.add(Subscription(user_id=paye.id, plan=SubscriptionPlan.PRO, status=SubscriptionStatus.ACTIVE,
                        current_period_end=datetime.now(timezone.utc) + timedelta(days=30)))
    make_user(db)  # arrivé sans lien
    db.commit()
    lignes = {l["source"]: l for l in bilan(db)}
    assert lignes["tiktok"] == {"source": "tiktok", "visites": 10, "inscriptions": 3, "abonnes": 1}
    assert lignes["insta"] == {"source": "insta", "visites": 1, "inscriptions": 0, "abonnes": 0}
    assert lignes["sans lien"] == {"source": "sans lien", "visites": None, "inscriptions": 1, "abonnes": 0}
    assert "youtube" not in lignes  # réseau jamais utilisé : pas de ligne


def test_bilan_depuis_filtre_les_visites(db):
    compter_visite(db, "tiktok", date(2026, 9, 1))
    compter_visite(db, "tiktok", date(2026, 10, 1))
    assert {l["source"]: l["visites"] for l in bilan(db, depuis=date(2026, 9, 15))}.get("tiktok") == 1


def test_outil_affiche_le_tableau(db, monkeypatch):
    compter_visite(db, "tiktok")
    u = make_user(db)
    u.signup_source = "tiktok"
    db.commit()
    sortie = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", type("S", (), {"buffer": sortie, "flush": lambda self: None})())
    assert outil.main([], session_factory=lambda: db) == 0
    texte = sortie.getvalue().decode("utf-8")
    assert "tiktok" in texte and "100.0 %" in texte  # 1 visite → 1 inscrit


def test_bilan_depuis_filtre_les_inscriptions(db):
    u = make_user(db)
    u.signup_source = "insta"
    db.commit()
    from app.services.sources import aujourdhui
    j = aujourdhui()
    assert {l["source"]: l["inscriptions"] for l in bilan(db, depuis=j)}.get("insta") == 1
    assert "insta" not in {l["source"] for l in bilan(db, depuis=j + timedelta(days=1))}
