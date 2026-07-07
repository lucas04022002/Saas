"""
Tests d'intégration pour les endpoints API.
Utilise FastAPI TestClient avec mocks pour la DB et les services.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Les secrets doivent être définis avant tout import de app
import os
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only-32chars")
os.environ.setdefault("CRON_SECRET", "test-cron-secret-key-for-pytest-32chars")
os.environ.setdefault("PREDICTION_PROVIDER", "mock")
os.environ["RUSHPLAY_SKIP_DB_INIT"] = "1"

from app.main import app
from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.models.enums import MatchStatus, RiskLevel, SubscriptionPlan, UserRole

# Désactive le startup PostgreSQL pour tous les tests
app.router.on_startup.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_db():
    db = MagicMock()
    db.scalars.return_value.unique.return_value.all.return_value = []
    db.scalars.return_value.all.return_value = []
    db.scalar.return_value = None
    db.execute.return_value.all.return_value = []
    return db


def _make_mock_match(match_id=None):
    m = MagicMock()
    m.id = match_id or uuid.uuid4()
    m.home_team = "Paris Saint-Germain"
    m.away_team = "Olympique de Marseille"
    m.league = "Ligue 1"
    m.country = "France"
    m.kickoff_at = datetime(2026, 4, 1, 20, 0, tzinfo=timezone.utc)
    m.status = MatchStatus.SCHEDULED
    m.last_analyzed_at = None
    m.analysis = None
    m.team_stats = []
    return m


def _make_mock_analysis():
    a = MagicMock()
    a.match_id = uuid.uuid4()
    a.confidence_score = 65.0
    a.recommended_bet = "Victoire domicile"
    a.bookmaker_odds = 1.95
    a.value_percent = 12.3
    a.risk_level = RiskLevel.LOW
    a.ai_explanation = "Le modele donne 65% sur Victoire domicile."
    a.warning_points = []
    a.created_at = datetime(2026, 3, 21, 8, 0, tzinfo=timezone.utc)
    a.updated_at = datetime(2026, 3, 21, 8, 0, tzinfo=timezone.utc)
    return a


def _make_mock_user(role=UserRole.USER, plan=SubscriptionPlan.STARTER):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.first_name = "Lucas"
    u.email = "lucas@test.com"
    u.password_hash = hash_password("password123")
    u.role = role
    u.subscription_plan = plan
    return u


# ---------------------------------------------------------------------------
# Fixture client
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Client de test avec DB mockée."""
    mock_db = _make_mock_db()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client():
    """Client de test avec un utilisateur authentifié."""
    mock_db = _make_mock_db()
    mock_user = _make_mock_user()
    token = create_access_token(str(mock_user.id))

    def override_get_db():
        yield mock_db

    mock_db.get.return_value = mock_user
    mock_db.scalar.return_value = mock_user

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock_db, mock_user, token
    app.dependency_overrides.clear()


@pytest.fixture
def authed_pro_client():
    """Client authentifié avec un abonnement PRO (accès premium)."""
    mock_db = _make_mock_db()
    mock_user = _make_mock_user(plan=SubscriptionPlan.PRO)
    token = create_access_token(str(mock_user.id))

    def override_get_db():
        yield mock_db

    mock_db.get.return_value = mock_user
    mock_db.scalar.return_value = mock_user

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock_db, mock_user, token
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(client):
    c, _ = client
    resp = c.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "prediction_provider" in data["data"]


# ---------------------------------------------------------------------------
# /api/v1/predictions
# ---------------------------------------------------------------------------

def test_prediction_health(client):
    c, _ = client
    resp = c.get("/api/v1/predictions/health")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_predict_match_success(client):
    c, _ = client
    resp = c.post("/api/v1/predictions/match", json={
        "home_team": "PSG",
        "away_team": "Lyon",
        "league": "Ligue 1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "confidence_score" in data["data"]
    assert "recommended_bet" in data["data"]
    assert "probabilities" in data["data"]


def test_predict_match_missing_fields(client):
    c, _ = client
    resp = c.post("/api/v1/predictions/match", json={"home_team": "PSG"})
    assert resp.status_code == 422


def test_predict_match_empty_team(client):
    c, _ = client
    resp = c.post("/api/v1/predictions/match", json={"home_team": "", "away_team": "Lyon"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/matches
# ---------------------------------------------------------------------------

def test_list_matches_empty(client):
    c, db = client
    db.scalar.return_value = 0
    db.scalars.return_value.unique.return_value.all.return_value = []

    resp = c.get("/api/v1/matches")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["items"] == []
    assert data["data"]["pagination"]["page"] == 1


def test_list_matches_with_results(client):
    c, db = client
    mock_match = _make_mock_match()
    db.scalar.return_value = 1
    db.scalars.return_value.unique.return_value.all.return_value = [mock_match]

    resp = c.get("/api/v1/matches")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["home_team"] == "Paris Saint-Germain"


def test_list_matches_pagination(client):
    c, db = client
    db.scalar.return_value = 0
    db.scalars.return_value.unique.return_value.all.return_value = []

    resp = c.get("/api/v1/matches?page=2&limit=5")
    assert resp.status_code == 200
    pagination = resp.json()["data"]["pagination"]
    assert pagination["page"] == 2
    assert pagination["limit"] == 5


def test_list_matches_invalid_sort(client):
    c, _ = client
    resp = c.get("/api/v1/matches?sort_by=invalid_field")
    assert resp.status_code == 422


def test_get_match_detail_not_found(client):
    c, db = client
    db.scalar.return_value = None
    resp = c.get(f"/api/v1/matches/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


def test_get_match_detail_found(client):
    c, db = client
    match_id = uuid.uuid4()
    mock_match = _make_mock_match(match_id)
    db.scalar.return_value = mock_match

    resp = c.get(f"/api/v1/matches/{match_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["home_team"] == "Paris Saint-Germain"
    assert data["analysis"] is None
    assert data["team_stats"] == []


# ---------------------------------------------------------------------------
# /api/v1/analyses
# ---------------------------------------------------------------------------

def test_list_analyses_empty(client):
    c, db = client
    db.execute.return_value.all.return_value = []

    resp = c.get("/api/v1/analyses")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_get_analysis_requires_auth(client):
    c, _ = client
    resp = c.get(f"/api/v1/analyses/{uuid.uuid4()}")
    assert resp.status_code == 401


def test_get_analysis_forbidden_for_starter(authed_client):
    c, db, _, token = authed_client
    db.scalar.return_value = None
    resp = c.get(
        f"/api/v1/analyses/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_get_analysis_not_found(authed_pro_client):
    c, db, _, token = authed_pro_client
    db.scalar.return_value = None  # get_current_user utilise db.get, pas db.scalar
    resp = c.get(
        f"/api/v1/analyses/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_get_analysis_found(authed_pro_client):
    c, db, _, token = authed_pro_client
    mock_analysis = _make_mock_analysis()
    db.scalar.return_value = mock_analysis

    resp = c.get(
        f"/api/v1/analyses/{mock_analysis.match_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["confidence_score"] == 65.0
    assert data["recommended_bet"] == "Victoire domicile"


# ---------------------------------------------------------------------------
# /api/v1/auth
# ---------------------------------------------------------------------------

def test_signup_success(client):
    c, db = client
    db.scalar.return_value = None  # pas d'utilisateur existant

    # SQLAlchemy n'applique pas les defaults de colonne sans vrai flush.
    # On simule ce comportement via le side_effect de flush.
    captured = []
    db.add.side_effect = lambda obj: captured.append(obj)

    def apply_orm_defaults():
        for obj in captured:
            if getattr(obj, "role", None) is None and hasattr(obj, "role"):
                obj.role = UserRole.USER
            if getattr(obj, "subscription_plan", None) is None and hasattr(obj, "subscription_plan"):
                obj.subscription_plan = SubscriptionPlan.STARTER

    db.flush.side_effect = apply_orm_defaults

    resp = c.post("/api/v1/auth/signup", json={
        "first_name": "Lucas",
        "email": "lucas@test.com",
        "password": "password123",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["user"]["email"] == "lucas@test.com"


def test_signup_duplicate_email(client):
    c, db = client
    db.scalar.return_value = _make_mock_user()  # utilisateur existant

    resp = c.post("/api/v1/auth/signup", json={
        "first_name": "Lucas",
        "email": "lucas@test.com",
        "password": "password123",
    })
    assert resp.status_code == 409
    assert resp.json()["success"] is False


def test_login_invalid_credentials(client):
    c, db = client
    db.scalar.return_value = None  # aucun utilisateur trouvé

    resp = c.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_login_wrong_password(client):
    c, db = client
    mock_user = _make_mock_user()
    db.scalar.return_value = mock_user  # utilisateur trouvé mais mauvais mot de passe

    resp = c.post("/api/v1/auth/login", json={
        "email": "lucas@test.com",
        "password": "wrong_password",
    })
    assert resp.status_code == 401


def test_me_without_token(client):
    c, _ = client
    resp = c.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_valid_token(authed_client):
    c, db, mock_user, token = authed_client
    resp = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == mock_user.email


def test_me_with_invalid_token(client):
    c, _ = client
    resp = c.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /api/v1/cron
# ---------------------------------------------------------------------------

def test_cron_without_key(client):
    c, _ = client
    resp = c.post("/api/v1/cron/daily-run")
    assert resp.status_code == 401


def test_cron_with_wrong_key(client):
    c, _ = client
    resp = c.post("/api/v1/cron/daily-run", headers={"X-CRON-KEY": "wrong-key"})
    assert resp.status_code == 401


def test_cron_with_valid_key(client):
    c, db = client
    db.scalars.return_value.all.return_value = []

    resp = c.post(
        "/api/v1/cron/daily-run",
        headers={"X-CRON-KEY": "test-cron-secret-key-for-pytest-32chars"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["processed"] == 0


# ---------------------------------------------------------------------------
# Paywall serveur — /api/v1/signal (réservé Pro/Elite)
# ---------------------------------------------------------------------------

def test_signal_requires_auth(client):
    c, _ = client
    resp = c.get(f"/api/v1/signal/{uuid.uuid4()}")
    assert resp.status_code == 401


def test_signal_forbidden_for_starter(authed_client):
    c, _, _, token = authed_client
    resp = c.get(
        f"/api/v1/signal/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_signal_ok_for_pro(authed_pro_client):
    c, db, _, token = authed_pro_client
    match = _make_mock_match()
    match.analysis = _make_mock_analysis()
    db.scalar.return_value = match  # get_current_user utilise db.get

    resp = c.get(
        f"/api/v1/signal/{match.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["analysis"]["recommended_bet"] == "Victoire domicile"


# ---------------------------------------------------------------------------
# Paywall serveur — /api/v1/matches masque les champs premium
# ---------------------------------------------------------------------------

def test_matches_locked_for_anonymous(client):
    c, db = client
    matches = []
    for conf in (70.0, 60.0, 50.0):
        m = _make_mock_match()
        a = _make_mock_analysis()
        a.confidence_score = conf
        m.analysis = a
        matches.append(m)
    db.scalar.return_value = 3
    db.scalars.return_value.unique.return_value.all.return_value = matches

    resp = c.get("/api/v1/matches")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 3
    locked = [it for it in items if it["locked"]]
    unlocked = [it for it in items if not it["locked"]]
    # FREE_SLOTS = 2 : deux signaux ouverts, le reste verrouillé
    assert len(unlocked) == 2
    assert len(locked) == 1
    assert locked[0]["recommended_bet"] is None
    assert locked[0]["value_percent"] is None


# ---------------------------------------------------------------------------
# Faille revenus — /api/v1/subscriptions/upgrade (admin uniquement)
# ---------------------------------------------------------------------------

def test_upgrade_forbidden_for_normal_user(authed_client):
    c, _, _, token = authed_client
    resp = c.post(
        "/api/v1/subscriptions/upgrade",
        json={"plan": "ELITE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
