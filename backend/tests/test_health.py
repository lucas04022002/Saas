import json
from datetime import datetime, timedelta, timezone

from app.collectors import run as runner


def test_health_reports_missing_and_fresh_heartbeats(client, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "HEARTBEATS", tmp_path)
    from app import main
    monkeypatch.setattr(main, "HEARTBEATS", tmp_path)
    d = client.get("/health").json()["data"]
    assert d["collectors"]["odds"] == {"at": None, "stale": True}
    (tmp_path / "odds.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat()}))
    (tmp_path / "fd_uk.json").write_text(json.dumps({"at": (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()}))
    d = client.get("/health").json()["data"]
    assert d["collectors"]["odds"]["stale"] is False and d["collectors"]["fd_uk"]["stale"] is True


def test_health_survives_corrupt_heartbeat(client, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "HEARTBEATS", tmp_path)
    from app import main
    monkeypatch.setattr(main, "HEARTBEATS", tmp_path)
    (tmp_path / "fd_org.json").write_text("{not json")
    (tmp_path / "odds.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat()}))
    d = client.get("/health").json()["data"]
    assert d["collectors"]["fd_org"] == {"at": None, "stale": True}
    assert d["collectors"]["odds"]["stale"] is False


def test_legal_endpoint(client):
    d = client.get("/api/v1/legal").json()["data"]
    assert d["minimum_age"] == 18 and "09 74 75 13 13" in d["warning"]
