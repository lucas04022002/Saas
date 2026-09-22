"""`/track-record` recalculait la grille de Poisson de tous les matchs terminés à chaque requête :
13,9 s en production sur 5 357 matchs, public, non borné (audit du 22/09/2026, E1).

Le résultat ne change qu'une fois par jour (arrivée des résultats) : il est gardé en mémoire une
heure par compétition. Les collecteurs tournent dans un autre processus, donc l'invalidation ne
peut être que temporelle."""
from app.api.v1.endpoints import track_record as tr


def _compte_calculs(monkeypatch):
    appels = {"n": 0}
    original = tr.compute_track_record

    def compte(db, competition):
        appels["n"] += 1
        return original(db, competition)

    monkeypatch.setattr(tr, "compute_track_record", compte)
    return appels


def test_deux_appels_dans_l_heure_ne_calculent_qu_une_fois(client, monkeypatch):
    tr.vider_le_cache()
    appels = _compte_calculs(monkeypatch)

    a = client.get("/api/v1/track-record").json()["data"]
    b = client.get("/api/v1/track-record").json()["data"]

    assert appels["n"] == 1
    assert a == b


def test_chaque_competition_a_sa_propre_entree(client, monkeypatch):
    tr.vider_le_cache()
    appels = _compte_calculs(monkeypatch)

    client.get("/api/v1/track-record?competition=E0")
    client.get("/api/v1/track-record?competition=F1")
    client.get("/api/v1/track-record?competition=E0")

    assert appels["n"] == 2


def test_passe_l_heure_le_resultat_est_recalcule(client, monkeypatch):
    tr.vider_le_cache()
    appels = _compte_calculs(monkeypatch)
    horloge = {"t": 1_000.0}
    monkeypatch.setattr(tr, "_maintenant", lambda: horloge["t"])

    client.get("/api/v1/track-record")
    horloge["t"] += tr.TTL_SECONDES - 1
    client.get("/api/v1/track-record")
    assert appels["n"] == 1

    horloge["t"] += 2
    client.get("/api/v1/track-record")
    assert appels["n"] == 2


def test_le_cache_n_est_pas_partage_entre_competition_et_global(client, monkeypatch):
    tr.vider_le_cache()
    appels = _compte_calculs(monkeypatch)
    client.get("/api/v1/track-record?competition=E0")
    client.get("/api/v1/track-record")
    assert appels["n"] == 2
