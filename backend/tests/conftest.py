import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only-32chars")
os.environ.setdefault("CRON_SECRET", "test-cron-secret-key-for-pytest-32chars")
os.environ["RUSHPLAY_SKIP_DB_INIT"] = "1"

from app.core.database import Base  # noqa: E402
from app import models  # noqa: E402,F401
from app.api.deps import get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import MatchStatus, SubscriptionPlan, UserRole  # noqa: E402
from app.models.match import Match  # noqa: E402
from app.models.team import Team  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, plan=SubscriptionPlan.STARTER, email=None):
    user = User(first_name="Test", email=email or f"{uuid.uuid4().hex[:8]}@test.fr",
                password_hash=hash_password("motdepasse123"), role=UserRole.USER, subscription_plan=plan)
    db.add(user); db.commit(); db.refresh(user)
    return user


def auth_header(user):
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def make_team(db, name):
    team = Team(name=name, country="Angleterre")
    db.add(team); db.commit(); db.refresh(team)
    return team


def make_match(db, home, away, competition="E0", kickoff=None, status=MatchStatus.SCHEDULED, home_score=None, away_score=None):
    """home/away : objets Team."""
    m = Match(competition=competition, league="Premier League", country="Angleterre",
              home_team_id=home.id, away_team_id=away.id, home_team=home.name, away_team=away.name,
              kickoff_at=kickoff or datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
              status=status, home_score=home_score, away_score=away_score)
    db.add(m); db.commit(); db.refresh(m)
    return m


@pytest.fixture
def starter_user(db):
    return make_user(db)


@pytest.fixture
def pro_user(db):
    return make_user(db, plan=SubscriptionPlan.PRO)
