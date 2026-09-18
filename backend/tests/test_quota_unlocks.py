"""Le quota du compte gratuit : deux matchs par semaine, ouverts explicitement.

Ces tests verrouillent ce qui casse en silence dans un paywall : un crédit
dépensé deux fois, un crédit dépensé sans clic, un quota qui ne se recharge
jamais, et un compte gratuit à qui on vendrait ce que paie l'abonné.
"""
from datetime import datetime, timedelta, timezone

from app.core.access import FREE_UNLOCKS_PER_WEEK, week_start
from app.models.match_unlock import MatchUnlock
from tests.conftest import auth_header, make_match
from tests.test_api_matches import seed_match_with_odds

NOW = datetime.now(timezone.utc)


def _second_match(db):
    from app.models.team import Team

    h = db.query(Team).filter_by(name="Arsenal").one()
    a = db.query(Team).filter_by(name="Chelsea").one()
    return make_match(db, a, h, kickoff=NOW + timedelta(days=3))


def test_sans_compte_le_deblocage_est_refuse(client, db):
    m = seed_match_with_odds(db)
    r = client.post(f"/api/v1/matches/{m.id}/unlock")
    assert r.status_code == 401


def test_un_compte_gratuit_ouvre_un_match_et_voit_favori_et_score(client, db, starter_user):
    m = seed_match_with_odds(db)
    head = auth_header(starter_user)

    # Avant : rien.
    d = client.get(f"/api/v1/matches/{m.id}", headers=head).json()["data"]
    assert d["locked"] is True and d["favourite"] is None and d["top_score"] is None

    r = client.post(f"/api/v1/matches/{m.id}/unlock", headers=head)
    assert r.status_code == 200
    assert r.json()["data"]["remaining"] == FREE_UNLOCKS_PER_WEEK - 1

    # Après : le favori et le score exact, et rien de ce que paie l'abonné.
    d = client.get(f"/api/v1/matches/{m.id}", headers=head).json()["data"]
    assert d["locked"] is False
    assert d["favourite"]["outcome"] == "home"
    assert d["top_score"]["score"].count("-") == 1
    assert d["books"] is None
    assert d["history"] is None
    assert d["movement"] is None
    assert d["score_distribution"] is None


def test_rouvrir_le_meme_match_ne_coute_pas_un_second_credit(client, db, starter_user):
    """Deux onglets, ou un double clic, ne doivent pas coûter deux crédits."""
    m = seed_match_with_odds(db)
    head = auth_header(starter_user)

    client.post(f"/api/v1/matches/{m.id}/unlock", headers=head)
    r = client.post(f"/api/v1/matches/{m.id}/unlock", headers=head)

    assert r.status_code == 200
    assert r.json()["data"]["used"] == 1
    assert db.query(MatchUnlock).filter_by(user_id=starter_user.id).count() == 1


def test_le_troisieme_match_de_la_semaine_est_refuse(client, db, starter_user):
    seed_match_with_odds(db)
    head = auth_header(starter_user)
    matchs = [seed_match_with_odds(db, kickoff=NOW + timedelta(days=i)) for i in (2, 3, 4)]

    for m in matchs[:FREE_UNLOCKS_PER_WEEK]:
        assert client.post(f"/api/v1/matches/{m.id}/unlock", headers=head).status_code == 200

    r = client.post(f"/api/v1/matches/{matchs[FREE_UNLOCKS_PER_WEEK].id}/unlock", headers=head)
    assert r.status_code == 402
    # L'application enveloppe ses erreurs : on cherche le mot dans la réponse
    # entière plutôt que de supposer la clé.
    assert "lundi" in r.text


def test_un_match_ouvert_la_semaine_derniere_reste_ouvert_et_ne_compte_plus(client, db, starter_user):
    """Le déblocage est définitif ; le quota, lui, se recharge."""
    m = seed_match_with_odds(db)
    head = auth_header(starter_user)

    db.add(
        MatchUnlock(
            user_id=starter_user.id,
            match_id=m.id,
            unlocked_at=week_start() - timedelta(days=2),
        )
    )
    db.commit()

    d = client.get(f"/api/v1/matches/{m.id}", headers=head).json()
    assert d["data"]["locked"] is False
    assert d["data"]["favourite"] is not None
    # Le crédit de la semaine dernière ne pèse pas sur celle-ci.
    assert d["data"]["quota"]["used"] == 0
    assert d["data"]["quota"]["remaining"] == FREE_UNLOCKS_PER_WEEK


def test_la_lecture_ne_consomme_jamais_de_credit(client, db, starter_user):
    """Le préchargement de Next.js ne doit pas vider le quota."""
    m = seed_match_with_odds(db)
    head = auth_header(starter_user)

    for _ in range(5):
        client.get(f"/api/v1/matches/{m.id}", headers=head)
        client.get("/api/v1/matches", headers=head)

    assert db.query(MatchUnlock).filter_by(user_id=starter_user.id).count() == 0


def test_l_abonne_voit_tout_sans_rien_depenser(client, db, pro_user):
    m = seed_match_with_odds(db)
    head = auth_header(pro_user)

    d = client.get(f"/api/v1/matches/{m.id}", headers=head).json()
    assert d["data"]["locked"] is False
    assert d["data"]["favourite"] is not None and d["data"]["top_score"] is not None
    assert d["data"]["books"] is not None
    assert d["data"]["quota"]["plan"] == "PRO"
    assert d["data"]["quota"]["remaining"] is None

    client.post(f"/api/v1/matches/{m.id}/unlock", headers=head)
    assert db.query(MatchUnlock).filter_by(user_id=pro_user.id).count() == 0


def test_la_liste_ne_montre_que_les_matchs_ouverts(client, db, starter_user):
    ouvert = seed_match_with_odds(db, kickoff=NOW + timedelta(days=2))
    seed_match_with_odds(db, kickoff=NOW + timedelta(days=3))
    head = auth_header(starter_user)

    client.post(f"/api/v1/matches/{ouvert.id}/unlock", headers=head)

    items = client.get("/api/v1/matches", headers=head).json()["data"]["items"]
    par_id = {it["id"]: it for it in items}

    assert par_id[str(ouvert.id)]["locked"] is False
    assert par_id[str(ouvert.id)]["favourite"] is not None
    assert par_id[str(ouvert.id)]["top_score"] is not None
    # L'écart entre bookmakers reste vendu, même sur un match ouvert.
    assert par_id[str(ouvert.id)]["best_gap"] is None

    autres = [it for it in items if it["id"] != str(ouvert.id)]
    assert autres and all(it["locked"] and it["favourite"] is None for it in autres)


def test_week_start_tombe_bien_un_lundi():
    for jour in range(14):
        moment = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc) + timedelta(days=jour)
        debut = week_start(moment)
        assert debut.weekday() == 0
        assert debut <= moment < debut + timedelta(days=7)
