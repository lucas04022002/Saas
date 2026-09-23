"""Les battements de cœur des collecteurs vivent en base (23/09/2026).

Ils étaient des fichiers dans `heartbeats/`, un volume créé autrefois par root. Depuis que le
conteneur tourne en utilisateur non privilégié (audit M4, 22/09), chaque collecteur écrivait ses
données puis échouait à la dernière ligne : `/health` affirmait « en panne » des collecteurs qui
marchaient. La base est déjà là, accessible, et survit aux redéploiements."""
from datetime import datetime, timedelta, timezone

from app.collectors import run as runner
from app.models.collector_heartbeat import CollectorHeartbeat


def test_health_reports_missing_and_fresh_heartbeats(client, db):
    d = client.get("/health").json()["data"]
    assert d["collectors"]["odds"] == {"at": None, "stale": True}

    runner.write_heartbeat(db, "odds", {"snapshots": 12})
    db.add(CollectorHeartbeat(name="fd_uk", at=datetime.now(timezone.utc) - timedelta(days=9), summary="{}")); db.commit()

    d = client.get("/health").json()["data"]
    assert d["collectors"]["odds"]["stale"] is False
    assert d["collectors"]["fd_uk"]["stale"] is True


def test_un_second_passage_met_a_jour_le_meme_battement(db):
    runner.write_heartbeat(db, "fd_org", {"created": 1})
    runner.write_heartbeat(db, "fd_org", {"created": 2})
    rows = db.query(CollectorHeartbeat).filter_by(name="fd_org").all()
    assert len(rows) == 1 and '"created": 2' in rows[0].summary


def test_le_battement_n_ecrit_rien_sur_le_disque(db, tmp_path, monkeypatch):
    """Le défaut du 22/09 : une écriture disque refusée. Plus aucune dépendance au système de fichiers."""
    monkeypatch.chdir(tmp_path)
    runner.write_heartbeat(db, "odds", {})
    assert list(tmp_path.iterdir()) == []


def test_legal_endpoint(client):
    d = client.get("/api/v1/legal").json()["data"]
    assert d["minimum_age"] == 18 and "09 74 75 13 13" in d["warning"]
