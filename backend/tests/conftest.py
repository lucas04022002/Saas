import os
import uuid
from unittest.mock import MagicMock

import pytest

# Fournit des secrets valides avant que settings soit importé
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only-32chars")
os.environ.setdefault("CRON_SECRET", "test-cron-secret-key-for-pytest-32chars")
os.environ.setdefault("PREDICTION_PROVIDER", "mock")

from app.models.match import Match  # noqa: E402
from app.providers.prediction.base import PredictionInput, PredictionResult  # noqa: E402
from app.providers.prediction.mock_provider import MockPredictionProvider  # noqa: E402
from app.services.prediction_service import PredictionService  # noqa: E402


@pytest.fixture
def mock_provider():
    return MockPredictionProvider()


@pytest.fixture
def prediction_svc(mock_provider):
    return PredictionService(provider=mock_provider, provider_name="mock")


@pytest.fixture
def sample_match():
    return Match(
        id=uuid.uuid4(),
        home_team="Paris Saint-Germain",
        away_team="Olympique de Marseille",
        league="Ligue 1",
        country="France",
        kickoff_at=__import__("datetime").datetime(2026, 4, 1, 20, 0),
        status=__import__("app.models.enums", fromlist=["MatchStatus"]).MatchStatus.SCHEDULED,
    )


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.scalar.return_value = None  # pas d'analyse existante par défaut
    return db
