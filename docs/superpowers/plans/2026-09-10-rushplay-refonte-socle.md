# RushPlay refonte — plan d'exécution du socle (base, collecteurs, moteur, API)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer le moteur ML de RushPlay par une lecture déterministe du marché (probabilités implicites, écarts bookmakers FR vs référence, mouvements, carnet de bankroll, texte par gabarits) alimentée par trois sources gratuites, et exposer le tout via l'API FastAPI existante. Le front sera fait ensuite avec Lucas ; ce plan livre l'API prête à consommer.

**Architecture:** Backend FastAPI + SQLAlchemy 2 + Alembic conservés (auth, users, subscriptions, favorites, paywall). On ajoute `teams`, `team_aliases`, `odds_snapshots`, `bets`, on étend `matches` (compétition, équipes canoniques). Trois collecteurs idempotents (`app/collectors/`) écrivent dans Postgres. Un module `app/engine/` pur Python calcule probabilités, favori, écarts, mouvements, forme et texte. Les routes lisent la base et appellent le moteur. Tout le ML est supprimé.

**Tech Stack:** Python 3.12, FastAPI 0.115, SQLAlchemy 2.0, Alembic, psycopg 3, requests, pytest. Tests d'intégration sur SQLite en mémoire via override de `get_db` (vérifié : `Base.metadata.create_all` des modèles actuels passe sur SQLite). Pas de Postgres ni Docker sur le PC de Lucas : les migrations Alembic sont vérifiées en mode hors-ligne (`alembic upgrade head --sql`) et appliquées sur le VPS.

## Global Constraints

- Dépôt : `C:\Users\lucas\OneDrive\Desktop\Saas--main - Copie` (remote `lucas04022002/Saas`, branche `master`). Travailler sur une branche `refonte-marche` créée depuis `master`.
- Répertoire de travail des commandes : `backend/`. Variables requises pour tout lancement : `JWT_SECRET=test-secret-key-for-pytest-only-32chars CRON_SECRET=test-cron-secret-key-for-pytest-32chars RUSHPLAY_SKIP_DB_INIT=1` (le `conftest.py` les pose déjà pour pytest).
- Format de réponse API inchangé : `{"success": bool, "message": str, "data": ...}` ; erreurs via `HTTPException` (handler global existant).
- Vocabulaire (spec §2) : « favori », « probabilité », « écart », « mouvement ». Interdits dans le code, les textes et les réponses : `value_bet`, `value_percent`, `confidence_score`, `recommended_bet`, `prediction`.
- Aucun accès réseau dans les tests : les collecteurs sont testés sur des fixtures JSON/CSV enregistrées dans `backend/tests/fixtures/`.
- Un nom d'équipe inconnu n'est jamais deviné : `TeamAliasError` → match en quarantaine (`status = QUARANTINE`) + log `WARNING`.
- Idempotence des collecteurs : relancer un relevé/import ne crée aucun doublon (contraintes uniques en base, upsert).
- Commits fréquents, messages en français, préfixes `feat:`, `refactor:`, `test:`, `chore:`.
- Toutes les compétitions V1 : codes `E0` (Premier League), `F1` (Ligue 1), `SP1` (La Liga), `D1` (Bundesliga), `I1` (Serie A), `CL` (Ligue des Champions).

---

## Structure des fichiers

```
backend/app/
  models/
    enums.py            MODIFIER : + MatchStatus.QUARANTINE, MatchStatus.POSTPONED, BetOutcome, BetStatus ; − RiskLevel, TeamType
    match.py            MODIFIER : + competition, home_team_id, away_team_id, fd_uk_key ; − relations analysis/team_stats
    team.py             CRÉER : Team, TeamAlias
    odds_snapshot.py    CRÉER : OddsSnapshot
    bet.py              CRÉER : Bet (carnet)
    analysis.py, team_stats.py, warning_point.py   SUPPRIMER
    __init__.py         MODIFIER : imports
  collectors/
    __init__.py         CRÉER
    competitions.py     CRÉER : table des compétitions (code ↔ clés The Odds API, football-data.org, football-data.co.uk)
    aliases.py          CRÉER : résolution des noms (resolve_team), TeamAliasError, seed des 98 équipes
    fd_uk.py            CRÉER : import résultats/historique football-data.co.uk (CSV)
    fd_org.py           CRÉER : calendrier + résultats football-data.org
    odds_api.py         CRÉER : relevés The Odds API → odds_snapshots
    run.py              CRÉER : point d'entrée CLI `python -m app.collectors.run <fd_uk|fd_org|odds> [--dry-run]`
  engine/
    __init__.py         CRÉER
    probabilities.py    CRÉER : implied(), margin(), reference()
    market.py           CRÉER : favourite(), gaps(), movement()
    context.py          CRÉER : form(), head_to_head()
    narrative.py        CRÉER : describe(MatchContext) -> str
    types.py            CRÉER : dataclasses BookOdds, Snapshot, MatchContext
  api/v1/endpoints/
    matches.py          RÉÉCRIRE : liste + détail (moteur)
    books.py            CRÉER : comparateur
    bankroll.py         CRÉER : carnet
    track_record.py     CRÉER : historique public
    analyses.py, opportunities.py, predictions.py, signal.py, cron.py   SUPPRIMER
  core/access.py        RÉÉCRIRE : gating sur les nouveaux champs
  services/             SUPPRIMER analysis_runner.py, form_fetcher.py, match_importer.py, odds_fetcher.py, prediction_service.py ; SUPPRIMER app/providers/
  main.py               MODIFIER : − prediction_service, + heartbeats dans /health
backend/alembic/versions/
    0005_market_reading.py   CRÉER
backend/tests/
    conftest.py         MODIFIER : fixture `db` SQLite + `client` avec override
    fixtures/           CRÉER : fd_uk_E0_sample.csv, fd_org_matches.json, odds_api_epl.json
    test_aliases.py, test_fd_uk.py, test_fd_org.py, test_odds_api.py,
    test_engine_probabilities.py, test_engine_market.py, test_engine_context.py, test_engine_narrative.py,
    test_api_matches.py, test_api_books.py, test_api_bankroll.py, test_api_track_record.py   CRÉER
    test_elo*.py, test_dixon_coles.py, test_kelly.py, test_mov.py, test_fatigue.py, test_home_advantage.py,
    test_poisson_par_competition.py, test_calibration.py, test_prediction_service.py, test_stats_collector.py,
    test_warning_points.py, test_api_endpoints.py   SUPPRIMER (test_security.py conservé)
racine du dépôt : prediction_engine.py, train_xgboost.py, backtesting.py, draw_policy.py, calibrate_draw_thresholds.py,
    *.json de backtest/modèle, xgboost_model.*, elo_ratings.json, team_stats.json, fixture_stats_cache.json,
    .github/workflows/keep-alive.yml, daily-analysis.yml, render.yaml, backend/scripts/   SUPPRIMER
```

---

### Task 1 : Branche, nettoyage du ML et suite de tests verte

**Files:**
- Delete: voir la liste « SUPPRIMER » ci-dessus (racine, `app/services/*`, `app/providers/`, endpoints ML, modèles ML, tests ML)
- Modify: `backend/app/main.py`, `backend/app/api/v1/router.py`, `backend/app/models/__init__.py`, `backend/app/models/match.py`, `backend/app/models/enums.py`, `backend/app/core/config.py`, `backend/requirements.txt`, `backend/tests/conftest.py`

**Interfaces:**
- Produces: une application qui démarre sans le ML, `pytest` vert (seuls `test_security.py` + un test de fumée restent), `Settings` sans `prediction_*`/`api_football_key`, avec `the_odds_api_key: str | None` et `football_data_org_key: str | None`.

- [ ] **Step 1 : créer la branche**

```bash
cd "C:/Users/lucas/OneDrive/Desktop/Saas--main - Copie" && git checkout -b refonte-marche
```

- [ ] **Step 2 : supprimer les fichiers ML à la racine et les béquilles de déploiement**

```bash
cd "C:/Users/lucas/OneDrive/Desktop/Saas--main - Copie" && git rm -q prediction_engine.py train_xgboost.py backtesting.py draw_policy.py calibrate_draw_thresholds.py drift_report.py prediction_tracker.py odds_logger.py collect_odds_season.py data_collector.py stats_collector.py features_avancees.py form_recente.py update_results.py verifier_ligues.py debug_fixture.py fuzz_fallback.py list_sports_odds_api.py test_api.py "import requests.py" "Algo plus APi.py" config.py config.example.py backtest_*.json draw_thresholds_by_league.json drift_report.json elo_ratings.json team_stats.json fixture_stats_cache.json historical_odds.json predictions_log.json xgboost_model.json xgboost_model.pkl .coverage render.yaml .github/workflows/keep-alive.yml .github/workflows/daily-analysis.yml && git rm -rq backend/scripts backend/app/providers && git rm -q backend/app/services/analysis_runner.py backend/app/services/form_fetcher.py backend/app/services/match_importer.py backend/app/services/odds_fetcher.py backend/app/services/prediction_service.py backend/app/api/v1/endpoints/analyses.py backend/app/api/v1/endpoints/opportunities.py backend/app/api/v1/endpoints/predictions.py backend/app/api/v1/endpoints/signal.py backend/app/api/v1/endpoints/cron.py backend/app/models/analysis.py backend/app/models/team_stats.py backend/app/models/warning_point.py && git rm -q backend/tests/test_elo.py backend/tests/test_elo_par_competition.py backend/tests/test_dixon_coles.py backend/tests/test_kelly.py backend/tests/test_mov.py backend/tests/test_fatigue.py backend/tests/test_home_advantage.py backend/tests/test_poisson_par_competition.py backend/tests/test_calibration.py backend/tests/test_prediction_service.py backend/tests/test_stats_collector.py backend/tests/test_warning_points.py backend/tests/test_api_endpoints.py
```

Les fichiers `*.md` de la racine (ANALYSE_*.md, GUIDE_*.md, …) décrivent l'ancien ML : les supprimer aussi (`git rm -q ANALYSE_ALGORITHME.md ANALYSE_MODELES.md COMMENT_AMELIORER_DONNEES.md COMPARAISON_VERSIONS.md CONFIGURATION_API.md EXPLICATION_FAVORI.md GUIDE_AMELIORATION_DONNEES.md GUIDE_BACKTESTING.md GUIDE_ENTRAINEMENT.md GUIDE_PREDICTION_AVANCEE.md INSTALLATION.txt LIGUES_CONFIGUREES.md RESUME_AMELIORATION.md RESUME_AMELIORATIONS.md TODO.md`). Garder `README.md`, `LICENSE.md`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`.

- [ ] **Step 3 : `backend/app/models/enums.py` — remplacer intégralement**

```python
import enum


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class SubscriptionPlan(str, enum.Enum):
    STARTER = "STARTER"
    PRO = "PRO"
    ELITE = "ELITE"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    QUARANTINE = "QUARANTINE"   # nom d'équipe non résolu : jamais affiché


class Outcome(str, enum.Enum):
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"


class BetStatus(str, enum.Enum):
    PENDING = "PENDING"
    WON = "WON"
    LOST = "LOST"
    VOID = "VOID"
```

- [ ] **Step 4 : `backend/app/models/match.py` — remplacer intégralement**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MatchStatus


class Match(Base):
    """Un match, à venir ou joué. Les résultats vivent ici (home_score/away_score, status FINISHED)."""

    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("competition", "kickoff_at", "home_team_id", "away_team_id", name="uq_match_natural"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)   # "fdo:<id>" (football-data.org)
    fd_uk_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)     # "E0:2025-08-15:Liverpool:Bournemouth"
    competition: Mapped[str] = mapped_column(String(8), nullable=False, index=True)             # E0, F1, SP1, D1, I1, CL
    home_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    away_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    home_team: Mapped[str] = mapped_column(String(120), nullable=False)   # nom canonique (copie pour l'affichage)
    away_team: Mapped[str] = mapped_column(String(120), nullable=False)
    league: Mapped[str] = mapped_column(String(120), nullable=False, index=True)   # libellé (« Premier League »)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), nullable=False, default=MatchStatus.SCHEDULED)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    home = relationship("Team", foreign_keys=[home_team_id])
    away = relationship("Team", foreign_keys=[away_team_id])
    favorites = relationship("Favorite", back_populates="match", cascade="all, delete-orphan")
    snapshots = relationship("OddsSnapshot", back_populates="match", cascade="all, delete-orphan", order_by="OddsSnapshot.taken_at")
    bets = relationship("Bet", back_populates="match")
```

- [ ] **Step 5 : `backend/app/models/__init__.py` — remplacer**

```python
from app.models.user import User  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.team import Team, TeamAlias  # noqa: F401
from app.models.match import Match  # noqa: F401
from app.models.favorite import Favorite  # noqa: F401
from app.models.odds_snapshot import OddsSnapshot  # noqa: F401
from app.models.bet import Bet  # noqa: F401
```

Les modèles `team.py`, `odds_snapshot.py`, `bet.py` sont créés en Task 2 ; pour que cette tâche soit verte seule, créer d'abord ces trois fichiers avec le contenu exact donné en Task 2 (Steps 1 à 3). Ils sont sans dépendance vers autre chose que `Base` et `enums`.

- [ ] **Step 6 : `backend/app/core/config.py` — retirer les champs ML, ajouter les clés des sources**

Remplacer les quatre lignes `prediction_provider`, `prediction_model_root`, `api_football_key`, `the_odds_api_key` par :

```python
    the_odds_api_key: str | None = None
    football_data_org_key: str | None = None
    fd_uk_base_url: str = "https://www.football-data.co.uk/mmz4281"
```

Supprimer l'import `Field` s'il devient inutilisé.

- [ ] **Step 7 : `backend/app/main.py` — retirer le service de prédiction et `runtime_migrations`**

Supprimer les lignes `from app.core.runtime_migrations import ensure_runtime_columns`, `from app.services.prediction_service import prediction_service`, le bloc `try: ensure_runtime_columns(engine) ...` dans `lifespan`, et remplacer la route `/health` par :

```python
@app.get("/health")
def health():
    return {"success": True, "message": "API healthy", "data": {"env": settings.env}}
```

(Task 10 y ajoutera les heartbeats des collecteurs.) Supprimer aussi `backend/app/core/runtime_migrations.py` (`git rm`).

- [ ] **Step 8 : `backend/app/api/v1/router.py` — remplacer**

```python
from fastapi import APIRouter

from app.api.v1.endpoints import auth, favorites, matches, subscriptions, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(matches.router)
api_router.include_router(favorites.router)
api_router.include_router(subscriptions.router)
```

- [ ] **Step 9 : `backend/app/api/v1/endpoints/matches.py` — version minimale provisoire (réécrite en Task 8)**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/matches", tags=["matches"])
```

- [ ] **Step 10 : `backend/app/core/access.py` — version minimale (réécrite en Task 8)**

```python
from app.models.enums import SubscriptionPlan
from app.models.user import User

PAID_PLANS = {SubscriptionPlan.PRO, SubscriptionPlan.ELITE}


def is_pro(user: User | None) -> bool:
    return user is not None and user.subscription_plan in PAID_PLANS
```

- [ ] **Step 11 : `backend/requirements.txt` — retirer numpy, scipy, xgboost, scikit-learn**

```
fastapi==0.115.0
uvicorn==0.30.6
sqlalchemy==2.0.36
psycopg[binary]==3.2.13
python-jose[cryptography]==3.3.0
bcrypt==5.0.0
pydantic==2.9.2
pydantic-settings==2.5.2
email-validator==2.2.0
httpx==0.27.2
requests==2.32.5
slowapi==0.1.9
alembic==1.18.4
python-json-logger==4.0.0
pytest==9.0.2
pytest-cov==7.0.0
```

- [ ] **Step 12 : `backend/tests/conftest.py` — remplacer intégralement (fixtures SQLite + client)**

```python
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
```

- [ ] **Step 13 : test de fumée `backend/tests/test_smoke.py`**

```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_signup_and_me(client):
    r = client.post("/api/v1/auth/signup", json={"first_name": "Lucas", "email": "lucas@test.fr", "password": "motdepasse123"})
    assert r.status_code in (200, 201), r.text
    token = r.json()["data"]["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["data"]["email"] == "lucas@test.fr"
```

Si le payload de signup exige d'autres champs (lire `app/api/v1/endpoints/auth.py` → `SignUpRequest`), adapter le JSON du test à ce schéma, sans modifier `auth.py`.

- [ ] **Step 14 : lancer les tests**

Run : `cd backend && python -m pytest -q`
Expected : `test_security.py` et `test_smoke.py` verts, zéro `ImportError`. Si un import vers un module supprimé subsiste (`grep -rn "prediction\|analysis_runner\|providers" app/`), le retirer.

- [ ] **Step 15 : commit**

```bash
git add -A && git commit -m "refactor: retire le moteur ML, les backtests et les béquilles Render ; tests SQLite en mémoire"
```

---

### Task 2 : Nouveaux modèles (Team, TeamAlias, OddsSnapshot, Bet) + migration Alembic 0005

**Files:**
- Create: `backend/app/models/team.py`, `backend/app/models/odds_snapshot.py`, `backend/app/models/bet.py`, `backend/alembic/versions/0005_market_reading.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Produces: `Team(id, name, country)`, `TeamAlias(source, alias, team_id)` avec unique `(source, alias)`, `OddsSnapshot(match_id, bookmaker, taken_at, home, draw, away)` avec unique `(match_id, bookmaker, taken_at)`, `Bet(user_id, match_id, outcome, bookmaker, odds, stake, status, payout, created_at, settled_at)`.

- [ ] **Step 1 : `backend/app/models/team.py`**

```python
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)   # nom canonique affiché
    country: Mapped[str] = mapped_column(String(120), nullable=False)

    aliases = relationship("TeamAlias", back_populates="team", cascade="all, delete-orphan")


class TeamAlias(Base):
    """Nom d'une équipe tel qu'écrit par une source. source ∈ {fd_uk, fd_org, odds_api}."""

    __tablename__ = "team_aliases"
    __table_args__ = (UniqueConstraint("source", "alias", name="uq_alias_source"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    alias: Mapped[str] = mapped_column(String(120), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    team = relationship("Team", back_populates="aliases")
```

- [ ] **Step 2 : `backend/app/models/odds_snapshot.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OddsSnapshot(Base):
    """Une photo des cotes 1N2 d'un bookmaker pour un match, à un instant. Jamais modifiée."""

    __tablename__ = "odds_snapshots"
    __table_args__ = (UniqueConstraint("match_id", "bookmaker", "taken_at", name="uq_snapshot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    bookmaker: Mapped[str] = mapped_column(String(40), nullable=False)    # clé The Odds API : betclic_fr, winamax_fr, unibet_fr, pmu_fr, netbet_fr, pinnacle ; ou fd_uk_avg / fd_uk_pinnacle
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    home: Mapped[float] = mapped_column(Float, nullable=False)
    draw: Mapped[float] = mapped_column(Float, nullable=False)
    away: Mapped[float] = mapped_column(Float, nullable=False)

    match = relationship("Match", back_populates="snapshots")
```

- [ ] **Step 3 : `backend/app/models/bet.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import BetStatus, Outcome


class Bet(Base):
    """Carnet de bankroll : un pari saisi par le client, réglé automatiquement au résultat."""

    __tablename__ = "bets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    outcome: Mapped[Outcome] = mapped_column(Enum(Outcome), nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(40), nullable=False)
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[BetStatus] = mapped_column(Enum(BetStatus), nullable=False, default=BetStatus.PENDING)
    payout: Mapped[float | None] = mapped_column(Float, nullable=True)   # gain brut (mise × cote) si gagné, 0 si perdu, mise si annulé
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    match = relationship("Match", back_populates="bets")
```

- [ ] **Step 4 : test `backend/tests/test_models.py`**

```python
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.odds_snapshot import OddsSnapshot
from app.models.team import TeamAlias
from tests.conftest import make_match, make_team


def test_snapshot_unique_per_match_bookmaker_time(db):
    h, a = make_team(db, "Arsenal"), make_team(db, "Chelsea")
    m = make_match(db, h, a)
    t = datetime(2026, 9, 12, 8, 0, tzinfo=timezone.utc)
    db.add(OddsSnapshot(match_id=m.id, bookmaker="betclic_fr", taken_at=t, home=1.9, draw=3.5, away=4.0)); db.commit()
    db.add(OddsSnapshot(match_id=m.id, bookmaker="betclic_fr", taken_at=t, home=1.95, draw=3.5, away=4.0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_alias_unique_per_source(db):
    h = make_team(db, "Manchester United")
    db.add(TeamAlias(source="fd_uk", alias="Man United", team_id=h.id)); db.commit()
    db.add(TeamAlias(source="fd_uk", alias="Man United", team_id=h.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_match_natural_key_unique(db):
    h, a = make_team(db, "Lyon"), make_team(db, "Marseille")
    make_match(db, h, a, competition="F1")
    with pytest.raises(IntegrityError):
        make_match(db, h, a, competition="F1")
    db.rollback()
```

- [ ] **Step 5 : lancer, vérifier vert**

Run : `cd backend && python -m pytest tests/test_models.py -v`
Expected : 3 PASS.

- [ ] **Step 6 : migration `backend/alembic/versions/0005_market_reading.py`**

```python
"""lecture du marché : teams, team_aliases, odds_snapshots, bets ; matches étendu ; tables ML supprimées

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-10
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS warning_points CASCADE")
    op.execute("DROP TABLE IF EXISTS team_stats CASCADE")
    op.execute("DROP TABLE IF EXISTS analyses CASCADE")
    op.execute("DROP TYPE IF EXISTS risklevel")
    op.execute("DROP TYPE IF EXISTS teamtype")
    op.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL UNIQUE,
            country VARCHAR(120) NOT NULL
        )""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS team_aliases (
            id UUID PRIMARY KEY,
            source VARCHAR(16) NOT NULL,
            alias VARCHAR(120) NOT NULL,
            team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            CONSTRAINT uq_alias_source UNIQUE (source, alias)
        )""")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS fd_uk_key VARCHAR(160) UNIQUE")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition VARCHAR(8) NOT NULL DEFAULT 'E0'")
    op.execute("ALTER TABLE matches ALTER COLUMN competition DROP DEFAULT")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_competition ON matches (competition)")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_team_id UUID REFERENCES teams(id)")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_team_id UUID REFERENCES teams(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_home_team_id ON matches (home_team_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_away_team_id ON matches (away_team_id)")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_shots INTEGER")
    op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_shots INTEGER")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS home_team_ext_id")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS away_team_ext_id")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS last_analyzed_at")
    op.execute("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'POSTPONED'")
    op.execute("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'QUARANTINE'")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_match_natural') THEN
                ALTER TABLE matches ADD CONSTRAINT uq_match_natural UNIQUE (competition, kickoff_at, home_team_id, away_team_id);
            END IF;
        END $$""")
    op.execute("""
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id UUID PRIMARY KEY,
            match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            bookmaker VARCHAR(40) NOT NULL,
            taken_at TIMESTAMPTZ NOT NULL,
            home DOUBLE PRECISION NOT NULL,
            draw DOUBLE PRECISION NOT NULL,
            away DOUBLE PRECISION NOT NULL,
            CONSTRAINT uq_snapshot UNIQUE (match_id, bookmaker, taken_at)
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_odds_snapshots_match_id ON odds_snapshots (match_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_odds_snapshots_taken_at ON odds_snapshots (taken_at)")
    op.execute("DO $$ BEGIN CREATE TYPE outcome AS ENUM ('home','draw','away'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE betstatus AS ENUM ('PENDING','WON','LOST','VOID'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            match_id UUID NOT NULL REFERENCES matches(id),
            outcome outcome NOT NULL,
            bookmaker VARCHAR(40) NOT NULL,
            odds DOUBLE PRECISION NOT NULL,
            stake DOUBLE PRECISION NOT NULL,
            status betstatus NOT NULL DEFAULT 'PENDING',
            payout DOUBLE PRECISION,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            settled_at TIMESTAMPTZ
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bets_user_id ON bets (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bets_match_id ON bets (match_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bets")
    op.execute("DROP TABLE IF EXISTS odds_snapshots")
    op.execute("ALTER TABLE matches DROP CONSTRAINT IF EXISTS uq_match_natural")
    op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS home_team_id, DROP COLUMN IF EXISTS away_team_id, DROP COLUMN IF EXISTS competition, DROP COLUMN IF EXISTS fd_uk_key, DROP COLUMN IF EXISTS home_shots, DROP COLUMN IF EXISTS away_shots")
    op.execute("DROP TABLE IF EXISTS team_aliases")
    op.execute("DROP TABLE IF EXISTS teams")
    op.execute("DROP TYPE IF EXISTS betstatus")
    op.execute("DROP TYPE IF EXISTS outcome")
```

Note : le nom du type enum Postgres existant pour `MatchStatus` est `matchstatus` (nom par défaut SQLAlchemy = nom de la classe en minuscules), à vérifier dans `0001_initial_schema.py` ; si c'est `match_status`, adapter les deux `ALTER TYPE`.

- [ ] **Step 7 : vérifier la migration hors-ligne (aucune base requise)**

Run : `cd backend && JWT_SECRET=test-secret-key-for-pytest-only-32chars CRON_SECRET=test-cron-secret-key-for-pytest-32chars alembic upgrade 0004:0005 --sql | head -40`
Expected : le SQL s'imprime sans exception Python. (`ALTER TYPE ... ADD VALUE` ne peut pas tourner dans une transaction sur Postgres < 12 ; le VPS aura Postgres 16, c'est accepté.)

- [ ] **Step 8 : commit**

```bash
git add -A && git commit -m "feat: modèles Team/TeamAlias/OddsSnapshot/Bet, matches étendu, migration 0005"
```

---

### Task 3 : Compétitions et résolution des noms d'équipes

**Files:**
- Create: `backend/app/collectors/__init__.py` (vide), `backend/app/collectors/competitions.py`, `backend/app/collectors/aliases.py`
- Test: `backend/tests/test_aliases.py`

**Interfaces:**
- Produces: `COMPETITIONS: dict[str, Competition]` (dataclass `Competition(code, name, country, odds_api_key, fd_org_code, fd_uk_code)`) ; `resolve_team(db, source: str, alias: str) -> Team` levant `TeamAliasError(source, alias)` ; `seed_aliases(db) -> int` (nombre d'alias créés) ; `KNOWN_TEAMS: list[tuple[str, str, dict[str, list[str]]]]` = (nom canonique, pays, {source: [alias, ...]}).

- [ ] **Step 1 : `backend/app/collectors/competitions.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Competition:
    code: str          # clé interne et football-data.co.uk (E0, F1, SP1, D1, I1) ; CL n'existe pas chez fd_uk
    name: str
    country: str
    odds_api_key: str  # The Odds API sport key
    fd_org_code: str   # football-data.org competition code
    fd_uk_code: str | None


COMPETITIONS: dict[str, Competition] = {
    "E0": Competition("E0", "Premier League", "Angleterre", "soccer_epl", "PL", "E0"),
    "F1": Competition("F1", "Ligue 1", "France", "soccer_france_ligue_one", "FL1", "F1"),
    "SP1": Competition("SP1", "La Liga", "Espagne", "soccer_spain_la_liga", "PD", "SP1"),
    "D1": Competition("D1", "Bundesliga", "Allemagne", "soccer_germany_bundesliga", "BL1", "D1"),
    "I1": Competition("I1", "Serie A", "Italie", "soccer_italy_serie_a", "SA", "I1"),
    "CL": Competition("CL", "Ligue des Champions", "Europe", "soccer_uefa_champs_league", "CL", None),
}

FRENCH_BOOKMAKERS = ("betclic_fr", "winamax_fr", "unibet_fr", "pmu_fr", "netbet_fr")
REFERENCE_BOOKMAKER = "pinnacle"


def by_odds_api_key(key: str) -> Competition | None:
    return next((c for c in COMPETITIONS.values() if c.odds_api_key == key), None)


def by_fd_org_code(code: str) -> Competition | None:
    return next((c for c in COMPETITIONS.values() if c.fd_org_code == code), None)
```

- [ ] **Step 2 : test `backend/tests/test_aliases.py` (écrire avant `aliases.py`)**

```python
import pytest

from app.collectors.aliases import KNOWN_TEAMS, TeamAliasError, resolve_team, seed_aliases
from app.models.team import Team


def test_seed_creates_98_domestic_teams(db):
    created = seed_aliases(db)
    assert db.query(Team).count() == 98
    assert created > 98            # chaque équipe a au moins un alias par source


def test_seed_is_idempotent(db):
    seed_aliases(db)
    n = db.query(Team).count()
    assert seed_aliases(db) == 0
    assert db.query(Team).count() == n


def test_resolve_known_alias_from_each_source(db):
    seed_aliases(db)
    assert resolve_team(db, "fd_uk", "Man United").name == "Manchester United"
    assert resolve_team(db, "odds_api", "Manchester United").name == "Manchester United"
    assert resolve_team(db, "fd_org", "Manchester United FC").name == "Manchester United"
    assert resolve_team(db, "fd_uk", "Paris SG").name == "Paris Saint-Germain"
    assert resolve_team(db, "fd_uk", "Ath Bilbao").name == "Athletic Bilbao"
    assert resolve_team(db, "fd_uk", "M'gladbach").name == "Borussia Mönchengladbach"


def test_resolve_is_accent_and_case_insensitive(db):
    seed_aliases(db)
    assert resolve_team(db, "odds_api", "  bayern MUNICH ").name == "Bayern Munich"


def test_unknown_alias_raises(db):
    seed_aliases(db)
    with pytest.raises(TeamAliasError) as e:
        resolve_team(db, "fd_uk", "FC Nulle Part")
    assert e.value.source == "fd_uk" and e.value.alias == "FC Nulle Part"


def test_known_teams_cover_five_leagues():
    countries = {country for _, country, _ in KNOWN_TEAMS}
    assert countries == {"Angleterre", "France", "Espagne", "Allemagne", "Italie"}
    assert len(KNOWN_TEAMS) == 98   # 20 + 18 + 20 + 18 + 20 (saison 2025/26) + 2 relégués 2024/25 utiles à l'historique
```

Run : `cd backend && python -m pytest tests/test_aliases.py -v` → Expected : `ImportError`.

- [ ] **Step 3 : `backend/app/collectors/aliases.py`**

Le tableau `KNOWN_TEAMS` doit contenir les 98 équipes des 5 championnats 2025/26 (les listes exactes par source sont dans la note de travail : noms football-data.co.uk relevés le 10/09/2026 dans les CSV `E0/F1/SP1/D1/I1_2526.csv`, noms The Odds API = noms anglais complets, noms football-data.org = nom + « FC »/« CF » selon le club). Structure :

```python
"""Résolution des noms d'équipes entre sources. Un nom inconnu lève TeamAliasError, jamais deviné."""
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team, TeamAlias

SOURCES = ("fd_uk", "fd_org", "odds_api")


class TeamAliasError(LookupError):
    def __init__(self, source: str, alias: str):
        super().__init__(f"nom d'équipe inconnu pour {source}: {alias!r}")
        self.source, self.alias = source, alias


def normalize(name: str) -> str:
    """minuscules, sans accents, espaces réduits — clé de comparaison des alias."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.lower().split())


# (nom canonique, pays, {source: [alias, ...]}) — le nom canonique est lui-même un alias implicite pour chaque source.
KNOWN_TEAMS: list[tuple[str, str, dict[str, list[str]]]] = [
    # ---- Angleterre (Premier League 2025/26)
    ("Arsenal", "Angleterre", {"fd_org": ["Arsenal FC"]}),
    ("Aston Villa", "Angleterre", {"fd_org": ["Aston Villa FC"]}),
    ("Bournemouth", "Angleterre", {"fd_org": ["AFC Bournemouth"]}),
    ("Brentford", "Angleterre", {"fd_org": ["Brentford FC"]}),
    ("Brighton", "Angleterre", {"fd_org": ["Brighton & Hove Albion FC"], "odds_api": ["Brighton and Hove Albion"]}),
    ("Burnley", "Angleterre", {"fd_org": ["Burnley FC"]}),
    ("Chelsea", "Angleterre", {"fd_org": ["Chelsea FC"]}),
    ("Crystal Palace", "Angleterre", {"fd_org": ["Crystal Palace FC"]}),
    ("Everton", "Angleterre", {"fd_org": ["Everton FC"]}),
    ("Fulham", "Angleterre", {"fd_org": ["Fulham FC"]}),
    ("Leeds", "Angleterre", {"fd_org": ["Leeds United FC"], "odds_api": ["Leeds United"]}),
    ("Liverpool", "Angleterre", {"fd_org": ["Liverpool FC"]}),
    ("Manchester City", "Angleterre", {"fd_uk": ["Man City"], "fd_org": ["Manchester City FC"]}),
    ("Manchester United", "Angleterre", {"fd_uk": ["Man United"], "fd_org": ["Manchester United FC"]}),
    ("Newcastle", "Angleterre", {"fd_org": ["Newcastle United FC"], "odds_api": ["Newcastle United"]}),
    ("Nottingham Forest", "Angleterre", {"fd_uk": ["Nott'm Forest"], "fd_org": ["Nottingham Forest FC"]}),
    ("Sunderland", "Angleterre", {"fd_org": ["Sunderland AFC"]}),
    ("Tottenham", "Angleterre", {"fd_org": ["Tottenham Hotspur FC"], "odds_api": ["Tottenham Hotspur"]}),
    ("West Ham", "Angleterre", {"fd_org": ["West Ham United FC"], "odds_api": ["West Ham United"]}),
    ("Wolves", "Angleterre", {"fd_org": ["Wolverhampton Wanderers FC"], "odds_api": ["Wolverhampton Wanderers"]}),
    # ---- France (Ligue 1 2025/26)
    ("Angers", "France", {"fd_org": ["Angers SCO"]}),
    ("Auxerre", "France", {"fd_org": ["AJ Auxerre"]}),
    ("Brest", "France", {"fd_org": ["Stade Brestois 29"], "odds_api": ["Stade Brestois 29"]}),
    ("Le Havre", "France", {"fd_org": ["Le Havre AC"]}),
    ("Lens", "France", {"fd_org": ["RC Lens"]}),
    ("Lille", "France", {"fd_org": ["Lille OSC"]}),
    ("Lorient", "France", {"fd_org": ["FC Lorient"]}),
    ("Lyon", "France", {"fd_org": ["Olympique Lyonnais"], "odds_api": ["Olympique Lyonnais"]}),
    ("Marseille", "France", {"fd_org": ["Olympique de Marseille"], "odds_api": ["Marseille", "Olympique Marseille"]}),
    ("Metz", "France", {"fd_org": ["FC Metz"]}),
    ("Monaco", "France", {"fd_org": ["AS Monaco FC"], "odds_api": ["AS Monaco"]}),
    ("Nantes", "France", {"fd_org": ["FC Nantes"]}),
    ("Nice", "France", {"fd_org": ["OGC Nice"]}),
    ("Paris FC", "France", {"fd_org": ["Paris FC"]}),
    ("Paris Saint-Germain", "France", {"fd_uk": ["Paris SG"], "fd_org": ["Paris Saint-Germain FC"], "odds_api": ["Paris Saint Germain", "Paris Saint-Germain"]}),
    ("Rennes", "France", {"fd_org": ["Stade Rennais FC 1901"], "odds_api": ["Stade Rennais"]}),
    ("Strasbourg", "France", {"fd_org": ["RC Strasbourg Alsace"]}),
    ("Toulouse", "France", {"fd_org": ["Toulouse FC"]}),
    # ---- Espagne (La Liga 2025/26)
    ("Alavés", "Espagne", {"fd_uk": ["Alaves"], "fd_org": ["Deportivo Alavés"], "odds_api": ["Alaves", "Deportivo Alaves"]}),
    ("Athletic Bilbao", "Espagne", {"fd_uk": ["Ath Bilbao"], "fd_org": ["Athletic Club"], "odds_api": ["Athletic Club", "Athletic Bilbao"]}),
    ("Atlético Madrid", "Espagne", {"fd_uk": ["Ath Madrid"], "fd_org": ["Club Atlético de Madrid"], "odds_api": ["Atletico Madrid", "Atlético Madrid"]}),
    ("Barcelona", "Espagne", {"fd_org": ["FC Barcelona"]}),
    ("Celta Vigo", "Espagne", {"fd_uk": ["Celta"], "fd_org": ["RC Celta de Vigo"]}),
    ("Elche", "Espagne", {"fd_org": ["Elche CF"]}),
    ("Espanyol", "Espagne", {"fd_uk": ["Espanol"], "fd_org": ["RCD Espanyol de Barcelona"]}),
    ("Getafe", "Espagne", {"fd_org": ["Getafe CF"]}),
    ("Girona", "Espagne", {"fd_org": ["Girona FC"]}),
    ("Levante", "Espagne", {"fd_org": ["Levante UD"]}),
    ("Mallorca", "Espagne", {"fd_org": ["RCD Mallorca"]}),
    ("Osasuna", "Espagne", {"fd_org": ["CA Osasuna"]}),
    ("Real Oviedo", "Espagne", {"fd_uk": ["Oviedo"], "fd_org": ["Real Oviedo"], "odds_api": ["Oviedo"]}),
    ("Rayo Vallecano", "Espagne", {"fd_uk": ["Vallecano"], "fd_org": ["Rayo Vallecano de Madrid"]}),
    ("Real Betis", "Espagne", {"fd_uk": ["Betis"], "fd_org": ["Real Betis Balompié"]}),
    ("Real Madrid", "Espagne", {"fd_org": ["Real Madrid CF"]}),
    ("Real Sociedad", "Espagne", {"fd_uk": ["Sociedad"], "fd_org": ["Real Sociedad de Fútbol"]}),
    ("Sevilla", "Espagne", {"fd_org": ["Sevilla FC"]}),
    ("Valencia", "Espagne", {"fd_org": ["Valencia CF"]}),
    ("Villarreal", "Espagne", {"fd_org": ["Villarreal CF"]}),
    # ---- Allemagne (Bundesliga 2025/26)
    ("Augsburg", "Allemagne", {"fd_org": ["FC Augsburg"], "odds_api": ["FC Augsburg"]}),
    ("Bayer Leverkusen", "Allemagne", {"fd_uk": ["Leverkusen"], "fd_org": ["Bayer 04 Leverkusen"]}),
    ("Bayern Munich", "Allemagne", {"fd_org": ["FC Bayern München"], "odds_api": ["Bayern München", "FC Bayern Munich"]}),
    ("Borussia Dortmund", "Allemagne", {"fd_uk": ["Dortmund"], "fd_org": ["Borussia Dortmund"]}),
    ("Borussia Mönchengladbach", "Allemagne", {"fd_uk": ["M'gladbach"], "fd_org": ["Borussia Mönchengladbach"], "odds_api": ["Borussia Monchengladbach"]}),
    ("Eintracht Frankfurt", "Allemagne", {"fd_uk": ["Ein Frankfurt"], "fd_org": ["Eintracht Frankfurt"]}),
    ("Freiburg", "Allemagne", {"fd_org": ["SC Freiburg"], "odds_api": ["SC Freiburg"]}),
    ("Hamburg", "Allemagne", {"fd_org": ["Hamburger SV"], "odds_api": ["Hamburger SV"]}),
    ("Heidenheim", "Allemagne", {"fd_org": ["1. FC Heidenheim 1846"], "odds_api": ["1. FC Heidenheim"]}),
    ("Hoffenheim", "Allemagne", {"fd_org": ["TSG 1899 Hoffenheim"], "odds_api": ["TSG Hoffenheim"]}),
    ("Köln", "Allemagne", {"fd_uk": ["FC Koln"], "fd_org": ["1. FC Köln"], "odds_api": ["FC Cologne", "1. FC Köln"]}),
    ("Mainz", "Allemagne", {"fd_org": ["1. FSV Mainz 05"], "odds_api": ["1. FSV Mainz 05"]}),
    ("RB Leipzig", "Allemagne", {"fd_org": ["RB Leipzig"]}),
    ("St. Pauli", "Allemagne", {"fd_uk": ["St Pauli"], "fd_org": ["FC St. Pauli 1910"], "odds_api": ["FC St. Pauli"]}),
    ("Stuttgart", "Allemagne", {"fd_org": ["VfB Stuttgart"], "odds_api": ["VfB Stuttgart"]}),
    ("Union Berlin", "Allemagne", {"fd_org": ["1. FC Union Berlin"]}),
    ("Werder Bremen", "Allemagne", {"fd_org": ["SV Werder Bremen"]}),
    ("Wolfsburg", "Allemagne", {"fd_org": ["VfL Wolfsburg"], "odds_api": ["VfL Wolfsburg"]}),
    # ---- Italie (Serie A 2025/26)
    ("Atalanta", "Italie", {"fd_org": ["Atalanta BC"]}),
    ("Bologna", "Italie", {"fd_org": ["Bologna FC 1909"]}),
    ("Cagliari", "Italie", {"fd_org": ["Cagliari Calcio"]}),
    ("Como", "Italie", {"fd_org": ["Como 1907"]}),
    ("Cremonese", "Italie", {"fd_org": ["US Cremonese"]}),
    ("Fiorentina", "Italie", {"fd_org": ["ACF Fiorentina"]}),
    ("Genoa", "Italie", {"fd_org": ["Genoa CFC"]}),
    ("Inter", "Italie", {"fd_org": ["FC Internazionale Milano"], "odds_api": ["Inter Milan"]}),
    ("Juventus", "Italie", {"fd_org": ["Juventus FC"]}),
    ("Lazio", "Italie", {"fd_org": ["SS Lazio"]}),
    ("Lecce", "Italie", {"fd_org": ["US Lecce"]}),
    ("Milan", "Italie", {"fd_org": ["AC Milan"], "odds_api": ["AC Milan"]}),
    ("Napoli", "Italie", {"fd_org": ["SSC Napoli"]}),
    ("Parma", "Italie", {"fd_org": ["Parma Calcio 1913"]}),
    ("Pisa", "Italie", {"fd_org": ["Pisa SC"]}),
    ("Roma", "Italie", {"fd_org": ["AS Roma"], "odds_api": ["AS Roma"]}),
    ("Sassuolo", "Italie", {"fd_org": ["US Sassuolo Calcio"]}),
    ("Torino", "Italie", {"fd_org": ["Torino FC"]}),
    ("Udinese", "Italie", {"fd_org": ["Udinese Calcio"]}),
    ("Verona", "Italie", {"fd_org": ["Hellas Verona FC"], "odds_api": ["Hellas Verona"]}),
    # ---- relégués 2024/25 présents dans l'historique fd_uk (utile à la forme et aux face-à-face)
    ("Leicester", "Angleterre", {"fd_org": ["Leicester City FC"], "odds_api": ["Leicester City"]}),
    ("Ipswich", "Angleterre", {"fd_org": ["Ipswich Town FC"], "odds_api": ["Ipswich Town"]}),
]


def seed_aliases(db: Session) -> int:
    """Crée les équipes et leurs alias manquants. Idempotent. Retourne le nombre d'alias créés."""
    created = 0
    existing_teams = {t.name: t for t in db.scalars(select(Team)).all()}
    existing_aliases = {(a.source, normalize(a.alias)) for a in db.scalars(select(TeamAlias)).all()}
    for name, country, per_source in KNOWN_TEAMS:
        team = existing_teams.get(name)
        if team is None:
            team = Team(name=name, country=country)
            db.add(team); db.flush()
            existing_teams[name] = team
        for source in SOURCES:
            for alias in [name, *per_source.get(source, [])]:
                key = (source, normalize(alias))
                if key in existing_aliases:
                    continue
                db.add(TeamAlias(source=source, alias=normalize(alias), team_id=team.id))
                existing_aliases.add(key); created += 1
    db.commit()
    return created


def resolve_team(db: Session, source: str, alias: str) -> Team:
    if source not in SOURCES:
        raise ValueError(f"source inconnue : {source}")
    row = db.scalar(select(TeamAlias).where(TeamAlias.source == source, TeamAlias.alias == normalize(alias)))
    if row is None:
        raise TeamAliasError(source, alias)
    return row.team
```

Les alias sont stockés **normalisés** (minuscules sans accents), ce qui rend la résolution insensible à la casse et aux accents. Le test `test_known_teams_cover_five_leagues` attend 98 entrées : 96 clubs 2025/26 + Leicester + Ipswich.

- [ ] **Step 4 : lancer**

Run : `cd backend && python -m pytest tests/test_aliases.py -v` → Expected : 6 PASS. Si le compte diffère de 98, compter `KNOWN_TEAMS` et corriger la liste (pas le test).

- [ ] **Step 5 : commit**

```bash
git add -A && git commit -m "feat: compétitions V1 et résolution des noms d'équipes (98 clubs, 3 sources, quarantaine sur inconnu)"
```

---

### Task 4 : Collecteur football-data.co.uk (historique + résultats + cotes ouverture/clôture)

**Files:**
- Create: `backend/app/collectors/fd_uk.py`, `backend/tests/fixtures/fd_uk_E0_sample.csv`
- Test: `backend/tests/test_fd_uk.py`

**Interfaces:**
- Consumes: `resolve_team`, `TeamAliasError`, `COMPETITIONS`, `Match`, `OddsSnapshot`.
- Produces: `parse_csv(text: str) -> list[FdUkRow]` (dataclass `FdUkRow(date: date, home: str, away: str, hg: int, ag: int, hs: int|None, as_: int|None, avg_open: tuple|None, avg_close: tuple|None, ps_open: tuple|None, ps_close: tuple|None)`), `import_rows(db, competition_code: str, rows: list[FdUkRow]) -> ImportReport` (dataclass `ImportReport(created: int, updated: int, quarantined: int, snapshots: int)`), `fetch_season(code: str, season: str) -> str` (texte CSV, `season` = "2526"), `run(db, seasons: list[str]) -> dict[str, ImportReport]`.

- [ ] **Step 1 : fixture `backend/tests/fixtures/fd_uk_E0_sample.csv`** — copier l'en-tête complet du vrai `E0_2526.csv` (voir la note de travail ; colonnes `Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,...,HS,AS,...,AvgH,AvgD,AvgA,...,PSH,PSD,PSA,...,AvgCH,AvgCD,AvgCA,...,PSCH,PSCD,PSCA,...`) suivi de 3 lignes réelles : `Liverpool` v `Bournemouth` 4-2 du 15/08/2025, `Man United` v `Arsenal` 0-1 du 17/08/2025, et une troisième ligne avec `HomeTeam` = `FC Nulle Part` (nom inconnu, pour la quarantaine). Les valeurs des colonnes non utilisées peuvent être vides.

- [ ] **Step 2 : test `backend/tests/test_fd_uk.py`**

```python
from datetime import date
from pathlib import Path

from app.collectors.aliases import seed_aliases
from app.collectors.fd_uk import import_rows, parse_csv
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot

SAMPLE = (Path(__file__).parent / "fixtures" / "fd_uk_E0_sample.csv").read_text(encoding="utf-8-sig")


def test_parse_csv_reads_scores_shots_and_odds():
    rows = parse_csv(SAMPLE)
    r = rows[0]
    assert (r.date, r.home, r.away, r.hg, r.ag) == (date(2025, 8, 15), "Liverpool", "Bournemouth", 4, 2)
    assert r.hs == 19 and r.as_ == 10
    assert r.avg_open == (1.31, 5.96, 8.31)
    assert r.avg_close is not None and r.ps_close is not None


def test_import_creates_finished_matches_and_two_snapshots(db):
    seed_aliases(db)
    report = import_rows(db, "E0", parse_csv(SAMPLE)[:2])
    assert (report.created, report.quarantined) == (2, 0)
    m = db.query(Match).filter(Match.home_team == "Liverpool").one()
    assert m.status == MatchStatus.FINISHED and (m.home_score, m.away_score) == (4, 2)
    assert m.competition == "E0" and m.home_team_id is not None
    books = sorted(s.bookmaker for s in db.query(OddsSnapshot).filter(OddsSnapshot.match_id == m.id))
    assert books == ["fd_uk_avg", "fd_uk_avg", "fd_uk_pinnacle", "fd_uk_pinnacle"]   # ouverture + clôture × 2 bookmakers
    assert report.snapshots == 8


def test_import_is_idempotent(db):
    seed_aliases(db)
    import_rows(db, "E0", parse_csv(SAMPLE)[:2])
    report = import_rows(db, "E0", parse_csv(SAMPLE)[:2])
    assert (report.created, report.updated, report.snapshots) == (0, 2, 0)
    assert db.query(Match).count() == 2 and db.query(OddsSnapshot).count() == 8


def test_unknown_team_goes_to_quarantine(db, caplog):
    seed_aliases(db)
    report = import_rows(db, "E0", parse_csv(SAMPLE))
    assert report.quarantined == 1
    q = db.query(Match).filter(Match.status == MatchStatus.QUARANTINE).one()
    assert q.home_team == "FC Nulle Part" and q.home_team_id is None
    assert any("FC Nulle Part" in rec.message and rec.levelname == "WARNING" for rec in caplog.records)
```

Run : `python -m pytest tests/test_fd_uk.py -v` → Expected : `ImportError`.

- [ ] **Step 3 : `backend/app/collectors/fd_uk.py`**

```python
"""football-data.co.uk : résultats, tirs et cotes d'ouverture/clôture (CSV par saison et championnat)."""
import csv
import io
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot

log = logging.getLogger("rushplay.collectors.fd_uk")


@dataclass
class FdUkRow:
    date: date
    home: str
    away: str
    hg: int
    ag: int
    hs: int | None
    as_: int | None
    avg_open: tuple[float, float, float] | None
    avg_close: tuple[float, float, float] | None
    ps_open: tuple[float, float, float] | None
    ps_close: tuple[float, float, float] | None


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    quarantined: int = 0
    snapshots: int = 0


def _f(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def _i(v: str | None) -> int | None:
    try:
        return int(v) if v not in (None, "") else None
    except ValueError:
        return None


def _triple(r: dict, h: str, d: str, a: str) -> tuple[float, float, float] | None:
    vals = (_f(r.get(h)), _f(r.get(d)), _f(r.get(a)))
    return None if any(v is None for v in vals) else vals  # type: ignore[return-value]


def parse_csv(text: str) -> list[FdUkRow]:
    rows = []
    for r in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        if not r.get("Date") or not r.get("FTR"):
            continue
        d, m, y = r["Date"].split("/")
        year = int(y) if len(y) == 4 else 2000 + int(y)
        rows.append(FdUkRow(
            date=date(year, int(m), int(d)), home=r["HomeTeam"].strip(), away=r["AwayTeam"].strip(),
            hg=int(r["FTHG"]), ag=int(r["FTAG"]), hs=_i(r.get("HS")), as_=_i(r.get("AS")),
            avg_open=_triple(r, "AvgH", "AvgD", "AvgA"), avg_close=_triple(r, "AvgCH", "AvgCD", "AvgCA"),
            ps_open=_triple(r, "PSH", "PSD", "PSA"), ps_close=_triple(r, "PSCH", "PSCD", "PSCA"),
        ))
    return rows


def _kickoff(d: date) -> datetime:
    """fd_uk ne donne pas d'heure fiable : on fixe 15:00 UTC ; l'heure exacte vient de fd_org quand elle existe."""
    return datetime.combine(d, time(15, 0), tzinfo=timezone.utc)


def _add_snapshot(db: Session, match: Match, bookmaker: str, taken_at: datetime, odds: tuple[float, float, float] | None) -> int:
    if odds is None:
        return 0
    exists = db.scalar(select(OddsSnapshot.id).where(OddsSnapshot.match_id == match.id, OddsSnapshot.bookmaker == bookmaker, OddsSnapshot.taken_at == taken_at))
    if exists:
        return 0
    db.add(OddsSnapshot(match_id=match.id, bookmaker=bookmaker, taken_at=taken_at, home=odds[0], draw=odds[1], away=odds[2]))
    return 1


def import_rows(db: Session, competition_code: str, rows: list[FdUkRow]) -> ImportReport:
    comp = COMPETITIONS[competition_code]
    report = ImportReport()
    for r in rows:
        key = f"{competition_code}:{r.date.isoformat()}:{r.home}:{r.away}"
        match = db.scalar(select(Match).where(Match.fd_uk_key == key))
        try:
            home, away = resolve_team(db, "fd_uk", r.home), resolve_team(db, "fd_uk", r.away)
        except TeamAliasError as e:
            log.warning("quarantaine fd_uk %s : %s", key, e)
            if match is None:
                db.add(Match(fd_uk_key=key, competition=competition_code, league=comp.name, country=comp.country,
                             home_team=r.home, away_team=r.away, kickoff_at=_kickoff(r.date), status=MatchStatus.QUARANTINE))
                db.commit()
            report.quarantined += 1
            continue
        if match is None:
            # un match créé par fd_org (calendrier) existe peut-être déjà : même compétition, mêmes équipes, même jour
            day_start = datetime.combine(r.date, time.min, tzinfo=timezone.utc)
            day_end = datetime.combine(r.date, time.max, tzinfo=timezone.utc)
            match = db.scalar(select(Match).where(Match.competition == competition_code, Match.home_team_id == home.id,
                                                  Match.away_team_id == away.id, Match.kickoff_at >= day_start, Match.kickoff_at <= day_end))
        if match is None:
            match = Match(fd_uk_key=key, competition=competition_code, league=comp.name, country=comp.country,
                          home_team_id=home.id, away_team_id=away.id, home_team=home.name, away_team=away.name,
                          kickoff_at=_kickoff(r.date))
            db.add(match); report.created += 1
        else:
            match.fd_uk_key = match.fd_uk_key or key
            report.updated += 1
        match.status, match.home_score, match.away_score = MatchStatus.FINISHED, r.hg, r.ag
        match.home_shots, match.away_shots = r.hs, r.as_
        db.flush()
        # cotes : ouverture datée J−7 12:00 UTC, clôture datée à l'heure du coup d'envoi (convention documentée)
        opening_at = datetime.combine(r.date, time(12, 0), tzinfo=timezone.utc).replace(day=r.date.day) - __import__("datetime").timedelta(days=7)
        closing_at = match.kickoff_at
        report.snapshots += _add_snapshot(db, match, "fd_uk_avg", opening_at, r.avg_open)
        report.snapshots += _add_snapshot(db, match, "fd_uk_avg", closing_at, r.avg_close)
        report.snapshots += _add_snapshot(db, match, "fd_uk_pinnacle", opening_at, r.ps_open)
        report.snapshots += _add_snapshot(db, match, "fd_uk_pinnacle", closing_at, r.ps_close)
        db.commit()
    return report


def fetch_season(code: str, season: str) -> str:
    url = f"{settings.fd_uk_base_url}/{season}/{code}.csv"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def run(db: Session, seasons: list[str]) -> dict[str, ImportReport]:
    """Importe les saisons demandées pour les 5 championnats fd_uk. `seasons` ex. ["2425", "2526"]."""
    out: dict[str, ImportReport] = {}
    for comp in COMPETITIONS.values():
        if comp.fd_uk_code is None:
            continue
        for season in seasons:
            rows = parse_csv(fetch_season(comp.fd_uk_code, season))
            out[f"{comp.code}:{season}"] = import_rows(db, comp.code, rows)
            log.info("fd_uk %s %s : %s", comp.code, season, out[f"{comp.code}:{season}"])
    return out
```

Remplacer la ligne compliquée `opening_at = ...` par la forme lisible :

```python
        from datetime import timedelta
        opening_at = datetime.combine(r.date - timedelta(days=7), time(12, 0), tzinfo=timezone.utc)
```

(mettre l'import `timedelta` en tête de fichier avec les autres).

- [ ] **Step 4 : lancer**

Run : `python -m pytest tests/test_fd_uk.py -v` → Expected : 4 PASS. Si `avg_open` du test ne correspond pas aux valeurs de la fixture, aligner la fixture sur la vraie ligne (`1.31,5.96,8.31` sont les `AvgH/AvgD/AvgA` réels de Liverpool–Bournemouth 2025/26).

- [ ] **Step 5 : commit**

```bash
git add -A && git commit -m "feat: collecteur football-data.co.uk (résultats, tirs, cotes ouverture/clôture, idempotent, quarantaine)"
```

---

### Task 5 : Collecteur football-data.org (calendrier, heures, Ligue des Champions, reports)

**Files:**
- Create: `backend/app/collectors/fd_org.py`, `backend/tests/fixtures/fd_org_matches.json`
- Test: `backend/tests/test_fd_org.py`

**Interfaces:**
- Consumes: `resolve_team`, `COMPETITIONS`, `by_fd_org_code`, `Match`.
- Produces: `parse_matches(payload: dict) -> list[FdOrgMatch]` (dataclass `FdOrgMatch(ext_id: str, competition_code: str, utc_date: datetime, home: str, away: str, status: str, hg: int|None, ag: int|None)`), `import_matches(db, items: list[FdOrgMatch]) -> ImportReport` (même dataclass que Task 4, importée de `fd_uk`), `fetch(competition_code: str, date_from: date, date_to: date) -> dict`, `run(db, days_ahead: int = 10, days_back: int = 3) -> ImportReport`.

- [ ] **Step 1 : fixture `backend/tests/fixtures/fd_org_matches.json`** — format réel de `GET /v4/competitions/PL/matches` (documenté sur football-data.org) :

```json
{
  "competition": {"code": "PL", "name": "Premier League"},
  "matches": [
    {"id": 537001, "utcDate": "2026-09-12T14:00:00Z", "status": "TIMED",
     "homeTeam": {"id": 57, "name": "Arsenal FC"}, "awayTeam": {"id": 61, "name": "Chelsea FC"},
     "score": {"fullTime": {"home": null, "away": null}}},
    {"id": 537002, "utcDate": "2026-09-06T15:00:00Z", "status": "FINISHED",
     "homeTeam": {"id": 64, "name": "Liverpool FC"}, "awayTeam": {"id": 1044, "name": "AFC Bournemouth"},
     "score": {"fullTime": {"home": 2, "away": 0}}},
    {"id": 537003, "utcDate": "2026-09-13T15:00:00Z", "status": "POSTPONED",
     "homeTeam": {"id": 66, "name": "Manchester United FC"}, "awayTeam": {"id": 73, "name": "Tottenham Hotspur FC"},
     "score": {"fullTime": {"home": null, "away": null}}},
    {"id": 537004, "utcDate": "2026-09-13T17:30:00Z", "status": "TIMED",
     "homeTeam": {"id": 999, "name": "FC Nulle Part"}, "awayTeam": {"id": 62, "name": "Everton FC"},
     "score": {"fullTime": {"home": null, "away": null}}}
  ]
}
```

- [ ] **Step 2 : test `backend/tests/test_fd_org.py`**

```python
import json
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.aliases import seed_aliases
from app.collectors.fd_org import import_matches, parse_matches
from app.models.enums import MatchStatus
from app.models.match import Match
from tests.conftest import make_match, make_team

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "fd_org_matches.json").read_text(encoding="utf-8"))


def test_parse_maps_status_and_scores():
    items = parse_matches(PAYLOAD)
    assert [i.status for i in items] == ["TIMED", "FINISHED", "POSTPONED", "TIMED"]
    assert items[1].hg == 2 and items[1].ag == 0 and items[0].hg is None
    assert items[0].utc_date == datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc)
    assert items[0].competition_code == "E0" and items[0].ext_id == "fdo:537001"


def test_import_creates_scheduled_finished_postponed_and_quarantine(db):
    seed_aliases(db)
    report = import_matches(db, parse_matches(PAYLOAD))
    assert (report.created, report.quarantined) == (3, 1)
    by_ext = {m.external_id: m for m in db.query(Match).all()}
    assert by_ext["fdo:537001"].status == MatchStatus.SCHEDULED
    assert by_ext["fdo:537002"].status == MatchStatus.FINISHED and by_ext["fdo:537002"].home_score == 2
    assert by_ext["fdo:537003"].status == MatchStatus.POSTPONED
    assert by_ext["fdo:537004"].status == MatchStatus.QUARANTINE


def test_import_updates_kickoff_of_match_created_by_fd_uk(db):
    """fd_uk crée le match à 15:00 UTC sans heure fiable ; fd_org apporte l'heure exacte et l'id externe."""
    seed_aliases(db)
    h, a = make_team(db, "Arsenal"), make_team(db, "Chelsea")
    m = make_match(db, h, a, kickoff=datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc))
    import_matches(db, parse_matches(PAYLOAD)[:1])
    db.refresh(m)
    assert m.external_id == "fdo:537001" and m.kickoff_at == datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc)
    assert db.query(Match).count() == 1


def test_import_is_idempotent(db):
    seed_aliases(db)
    import_matches(db, parse_matches(PAYLOAD))
    report = import_matches(db, parse_matches(PAYLOAD))
    assert report.created == 0 and db.query(Match).count() == 4
```

Note : `make_team(db, "Arsenal")` crée une équipe nommée « Arsenal » ; `seed_aliases` ensuite retrouve cette équipe par son nom (pas de doublon). Dans ce test, appeler `seed_aliases` **après** `make_team` n'est pas nécessaire puisque `seed_aliases` est appelé avant et crée déjà « Arsenal » : remplacer `make_team(db, "Arsenal")` par `db.query(Team).filter_by(name="Arsenal").one()` (importer `Team`). Idem pour Chelsea.

Run : `python -m pytest tests/test_fd_org.py -v` → Expected : `ImportError`.

- [ ] **Step 3 : `backend/app/collectors/fd_org.py`**

```python
"""football-data.org (plan gratuit) : calendrier, heures exactes, résultats, reports, Ligue des Champions."""
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS, by_fd_org_code
from app.collectors.fd_uk import ImportReport
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match

log = logging.getLogger("rushplay.collectors.fd_org")
BASE = "https://api.football-data.org/v4"

STATUS_MAP = {
    "SCHEDULED": MatchStatus.SCHEDULED, "TIMED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE, "PAUSED": MatchStatus.LIVE,
    "FINISHED": MatchStatus.FINISHED, "AWARDED": MatchStatus.FINISHED,
    "POSTPONED": MatchStatus.POSTPONED, "SUSPENDED": MatchStatus.POSTPONED, "CANCELLED": MatchStatus.POSTPONED,
}


@dataclass
class FdOrgMatch:
    ext_id: str
    competition_code: str
    utc_date: datetime
    home: str
    away: str
    status: str
    hg: int | None
    ag: int | None


def parse_matches(payload: dict) -> list[FdOrgMatch]:
    comp = by_fd_org_code(payload["competition"]["code"])
    if comp is None:
        return []
    out = []
    for m in payload.get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        out.append(FdOrgMatch(
            ext_id=f"fdo:{m['id']}", competition_code=comp.code,
            utc_date=datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")),
            home=m["homeTeam"]["name"], away=m["awayTeam"]["name"], status=m["status"],
            hg=ft.get("home"), ag=ft.get("away"),
        ))
    return out


def import_matches(db: Session, items: list[FdOrgMatch]) -> ImportReport:
    report = ImportReport()
    for it in items:
        comp = COMPETITIONS[it.competition_code]
        match = db.scalar(select(Match).where(Match.external_id == it.ext_id))
        try:
            home, away = resolve_team(db, "fd_org", it.home), resolve_team(db, "fd_org", it.away)
        except TeamAliasError as e:
            log.warning("quarantaine fd_org %s : %s", it.ext_id, e)
            if match is None:
                db.add(Match(external_id=it.ext_id, competition=comp.code, league=comp.name, country=comp.country,
                             home_team=it.home, away_team=it.away, kickoff_at=it.utc_date, status=MatchStatus.QUARANTINE))
                db.commit()
            report.quarantined += 1
            continue
        if match is None:
            day = it.utc_date.date()
            day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
            day_end = datetime.combine(day, time.max, tzinfo=timezone.utc)
            match = db.scalar(select(Match).where(Match.competition == comp.code, Match.home_team_id == home.id,
                                                  Match.away_team_id == away.id, Match.kickoff_at >= day_start, Match.kickoff_at <= day_end))
        if match is None:
            match = Match(external_id=it.ext_id, competition=comp.code, league=comp.name, country=comp.country,
                          home_team_id=home.id, away_team_id=away.id, home_team=home.name, away_team=away.name,
                          kickoff_at=it.utc_date)
            db.add(match); report.created += 1
        else:
            match.external_id = match.external_id or it.ext_id
            match.kickoff_at = it.utc_date
            report.updated += 1
        new_status = STATUS_MAP.get(it.status, MatchStatus.SCHEDULED)
        if match.status != MatchStatus.FINISHED or new_status == MatchStatus.FINISHED:
            match.status = new_status
        if new_status == MatchStatus.FINISHED and it.hg is not None:
            match.home_score, match.away_score = it.hg, it.ag
        db.commit()
    return report


def fetch(competition_code: str, date_from: date, date_to: date) -> dict:
    comp = COMPETITIONS[competition_code]
    headers = {"X-Auth-Token": settings.football_data_org_key or ""}
    resp = requests.get(f"{BASE}/competitions/{comp.fd_org_code}/matches",
                        params={"dateFrom": date_from.isoformat(), "dateTo": date_to.isoformat()}, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def run(db: Session, days_ahead: int = 10, days_back: int = 3) -> ImportReport:
    """Un appel par compétition (6 appels, plan gratuit = 10/min : dormir 7 s entre deux)."""
    import time as _time
    total = ImportReport()
    today = datetime.now(timezone.utc).date()
    for code in COMPETITIONS:
        payload = fetch(code, today - timedelta(days=days_back), today + timedelta(days=days_ahead))
        r = import_matches(db, parse_matches(payload))
        total.created += r.created; total.updated += r.updated; total.quarantined += r.quarantined
        log.info("fd_org %s : %s", code, r)
        _time.sleep(7)
    return total
```

- [ ] **Step 4 : lancer**

Run : `python -m pytest tests/test_fd_org.py -v` → Expected : 4 PASS.

- [ ] **Step 5 : commit**

```bash
git add -A && git commit -m "feat: collecteur football-data.org (calendrier, heures, LdC, reports, idempotent)"
```

---

### Task 6 : Collecteur The Odds API (relevés archivés, régions fr + eu)

**Files:**
- Create: `backend/app/collectors/odds_api.py`, `backend/tests/fixtures/odds_api_epl.json`, `backend/app/collectors/run.py`
- Test: `backend/tests/test_odds_api.py`

**Interfaces:**
- Consumes: `resolve_team`, `by_odds_api_key`, `FRENCH_BOOKMAKERS`, `REFERENCE_BOOKMAKER`, `Match`, `OddsSnapshot`.
- Produces: `parse_events(sport_key: str, payload: list) -> list[OddsEvent]` (dataclass `OddsEvent(competition_code, commence: datetime, home, away, books: dict[str, tuple[float,float,float]])`), `store_events(db, events, taken_at: datetime) -> StoreReport` (dataclass `StoreReport(snapshots: int, matched: int, unmatched: int, quarantined: int)`), `fetch_sport(sport_key: str) -> list`, `run(db) -> StoreReport`, et la CLI `python -m app.collectors.run {fd_uk,fd_org,odds,seed} [--seasons 2425 2526]`.

- [ ] **Step 1 : fixture `backend/tests/fixtures/odds_api_epl.json`** — format réel de `GET /v4/sports/soccer_epl/odds?regions=fr,eu&markets=h2h` :

```json
[
  {"id": "abc1", "sport_key": "soccer_epl", "commence_time": "2026-09-12T14:00:00Z",
   "home_team": "Arsenal", "away_team": "Chelsea",
   "bookmakers": [
     {"key": "betclic_fr", "title": "Betclic (FR)", "last_update": "2026-09-11T08:00:00Z",
      "markets": [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 1.95}, {"name": "Chelsea", "price": 3.9}, {"name": "Draw", "price": 3.6}]}]},
     {"key": "winamax_fr", "title": "Winamax (FR)", "last_update": "2026-09-11T08:00:00Z",
      "markets": [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 2.0}, {"name": "Chelsea", "price": 3.8}, {"name": "Draw", "price": 3.5}]}]},
     {"key": "pinnacle", "title": "Pinnacle", "last_update": "2026-09-11T08:00:00Z",
      "markets": [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 2.02}, {"name": "Chelsea", "price": 3.95}, {"name": "Draw", "price": 3.7}]}]},
     {"key": "williamhill", "title": "William Hill", "last_update": "2026-09-11T08:00:00Z",
      "markets": [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 1.9}, {"name": "Chelsea", "price": 3.8}, {"name": "Draw", "price": 3.5}]}]}
   ]},
  {"id": "abc2", "sport_key": "soccer_epl", "commence_time": "2026-09-13T17:30:00Z",
   "home_team": "FC Nulle Part", "away_team": "Everton",
   "bookmakers": [{"key": "betclic_fr", "title": "Betclic (FR)", "last_update": "2026-09-11T08:00:00Z",
      "markets": [{"key": "h2h", "outcomes": [{"name": "FC Nulle Part", "price": 2.5}, {"name": "Everton", "price": 2.8}, {"name": "Draw", "price": 3.2}]}]}]}
]
```

- [ ] **Step 2 : test `backend/tests/test_odds_api.py`**

```python
import json
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.aliases import seed_aliases
from app.collectors.odds_api import parse_events, store_events
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot
from app.models.team import Team
from tests.conftest import make_match

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "odds_api_epl.json").read_text(encoding="utf-8"))
T0 = datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc)


def test_parse_keeps_french_books_and_pinnacle_only():
    ev = parse_events("soccer_epl", PAYLOAD)[0]
    assert ev.competition_code == "E0" and (ev.home, ev.away) == ("Arsenal", "Chelsea")
    assert set(ev.books) == {"betclic_fr", "winamax_fr", "pinnacle"}      # williamhill écarté
    assert ev.books["betclic_fr"] == (1.95, 3.6, 3.9)                    # ordre domicile, nul, extérieur


def test_store_attaches_snapshots_to_existing_match(db):
    seed_aliases(db)
    h, a = db.query(Team).filter_by(name="Arsenal").one(), db.query(Team).filter_by(name="Chelsea").one()
    m = make_match(db, h, a, kickoff=datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc))
    report = store_events(db, parse_events("soccer_epl", PAYLOAD), taken_at=T0)
    assert (report.matched, report.snapshots, report.quarantined) == (1, 3, 1)
    snaps = db.query(OddsSnapshot).filter_by(match_id=m.id).all()
    assert {s.bookmaker for s in snaps} == {"betclic_fr", "winamax_fr", "pinnacle"} and all(s.taken_at == T0 for s in snaps)


def test_store_creates_match_when_calendar_missing(db):
    """Le calendrier fd_org peut être en retard : le match est créé SCHEDULED à partir de l'événement."""
    seed_aliases(db)
    report = store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    assert report.matched == 1
    m = db.query(Match).filter(Match.status == MatchStatus.SCHEDULED).one()
    assert (m.home_team, m.away_team, m.competition) == ("Arsenal", "Chelsea", "E0")


def test_store_is_idempotent_for_same_taken_at(db):
    seed_aliases(db)
    store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    report = store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    assert report.snapshots == 0 and db.query(OddsSnapshot).count() == 3


def test_second_reading_adds_new_snapshots(db):
    seed_aliases(db)
    store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=T0)
    store_events(db, parse_events("soccer_epl", PAYLOAD)[:1], taken_at=datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc))
    assert db.query(OddsSnapshot).count() == 6
```

Run : `python -m pytest tests/test_odds_api.py -v` → Expected : `ImportError`.

- [ ] **Step 3 : `backend/app/collectors/odds_api.py`**

```python
"""The Odds API : relevés 1N2 des bookmakers français + Pinnacle, archivés tels quels (jamais écrasés)."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.aliases import TeamAliasError, resolve_team
from app.collectors.competitions import COMPETITIONS, FRENCH_BOOKMAKERS, REFERENCE_BOOKMAKER, by_odds_api_key
from app.core.config import settings
from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.odds_snapshot import OddsSnapshot

log = logging.getLogger("rushplay.collectors.odds_api")
BASE = "https://api.the-odds-api.com/v4/sports"
KEPT_BOOKMAKERS = set(FRENCH_BOOKMAKERS) | {REFERENCE_BOOKMAKER}


@dataclass
class OddsEvent:
    competition_code: str
    commence: datetime
    home: str
    away: str
    books: dict[str, tuple[float, float, float]] = field(default_factory=dict)


@dataclass
class StoreReport:
    snapshots: int = 0
    matched: int = 0
    unmatched: int = 0
    quarantined: int = 0


def parse_events(sport_key: str, payload: list) -> list[OddsEvent]:
    comp = by_odds_api_key(sport_key)
    if comp is None:
        return []
    events = []
    for e in payload:
        ev = OddsEvent(competition_code=comp.code, commence=datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")),
                       home=e["home_team"], away=e["away_team"])
        for b in e.get("bookmakers", []):
            if b["key"] not in KEPT_BOOKMAKERS:
                continue
            h2h = next((m for m in b.get("markets", []) if m["key"] == "h2h"), None)
            if h2h is None:
                continue
            prices = {o["name"]: float(o["price"]) for o in h2h["outcomes"]}
            if ev.home in prices and ev.away in prices and "Draw" in prices:
                ev.books[b["key"]] = (prices[ev.home], prices["Draw"], prices[ev.away])
        if ev.books:
            events.append(ev)
    return events


def _find_or_create_match(db: Session, ev: OddsEvent, home, away) -> Match:
    comp = COMPETITIONS[ev.competition_code]
    day = ev.commence.date()
    window = (datetime.combine(day - timedelta(days=1), time.min, tzinfo=timezone.utc),
              datetime.combine(day + timedelta(days=1), time.max, tzinfo=timezone.utc))
    match = db.scalar(select(Match).where(Match.competition == comp.code, Match.home_team_id == home.id, Match.away_team_id == away.id,
                                          Match.kickoff_at >= window[0], Match.kickoff_at <= window[1]))
    if match is None:
        match = Match(competition=comp.code, league=comp.name, country=comp.country, home_team_id=home.id, away_team_id=away.id,
                      home_team=home.name, away_team=away.name, kickoff_at=ev.commence, status=MatchStatus.SCHEDULED)
        db.add(match); db.flush()
    return match


def store_events(db: Session, events: list[OddsEvent], taken_at: datetime) -> StoreReport:
    report = StoreReport()
    for ev in events:
        try:
            home, away = resolve_team(db, "odds_api", ev.home), resolve_team(db, "odds_api", ev.away)
        except TeamAliasError as e:
            log.warning("quarantaine odds_api %s v %s : %s", ev.home, ev.away, e)
            report.quarantined += 1
            continue
        match = _find_or_create_match(db, ev, home, away)
        report.matched += 1
        for book, (h, d, a) in ev.books.items():
            exists = db.scalar(select(OddsSnapshot.id).where(OddsSnapshot.match_id == match.id, OddsSnapshot.bookmaker == book, OddsSnapshot.taken_at == taken_at))
            if exists:
                continue
            db.add(OddsSnapshot(match_id=match.id, bookmaker=book, taken_at=taken_at, home=h, draw=d, away=a))
            report.snapshots += 1
        db.commit()
    return report


def fetch_sport(sport_key: str) -> list:
    """1 crédit par région → 2 crédits par compétition et par relevé."""
    resp = requests.get(f"{BASE}/{sport_key}/odds",
                        params={"apiKey": settings.the_odds_api_key, "regions": "fr,eu", "markets": "h2h", "oddsFormat": "decimal"}, timeout=30)
    resp.raise_for_status()
    remaining = resp.headers.get("x-requests-remaining")
    log.info("odds_api %s : %s événements, crédits restants %s", sport_key, len(resp.json()), remaining)
    return resp.json()


def run(db: Session) -> StoreReport:
    """Un relevé complet = 6 compétitions × 2 régions = 12 crédits. L'horodatage est arrondi à l'heure."""
    taken_at = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    total = StoreReport()
    for comp in COMPETITIONS.values():
        try:
            payload = fetch_sport(comp.odds_api_key)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                log.error("odds_api : quota épuisé ou clé invalide, arrêt propre du relevé")
                break
            raise
        r = store_events(db, parse_events(comp.odds_api_key, payload), taken_at)
        for k in ("snapshots", "matched", "unmatched", "quarantined"):
            setattr(total, k, getattr(total, k) + getattr(r, k))
    log.info("odds_api relevé %s : %s", taken_at.isoformat(), total)
    return total
```

- [ ] **Step 4 : `backend/app/collectors/run.py` (CLI + heartbeat)**

```python
"""CLI des collecteurs : python -m app.collectors.run {seed,fd_uk,fd_org,odds} [--seasons 2425 2526]
Écrit un heartbeat JSON dans backend/heartbeats/<nom>.json après chaque run réussi (lu par /health)."""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.api.deps import get_db
from app.collectors import fd_org, fd_uk, odds_api
from app.collectors.aliases import seed_aliases
from app.core.logging import setup_logging

HEARTBEATS = Path(__file__).resolve().parents[2] / "heartbeats"


def write_heartbeat(name: str, summary: dict) -> None:
    HEARTBEATS.mkdir(exist_ok=True)
    (HEARTBEATS / f"{name}.json").write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **summary}), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    p = argparse.ArgumentParser()
    p.add_argument("collector", choices=["seed", "fd_uk", "fd_org", "odds"])
    p.add_argument("--seasons", nargs="*", default=["2526"])
    args = p.parse_args(argv)
    db = next(get_db())
    try:
        if args.collector == "seed":
            n = seed_aliases(db); summary = {"aliases_created": n}
        elif args.collector == "fd_uk":
            reports = fd_uk.run(db, args.seasons); summary = {k: vars(v) for k, v in reports.items()}
        elif args.collector == "fd_org":
            summary = vars(fd_org.run(db))
        else:
            summary = vars(odds_api.run(db))
        write_heartbeat(args.collector, summary)
        logging.getLogger("rushplay.collectors").info("%s terminé : %s", args.collector, summary)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5 : lancer**

Run : `python -m pytest tests/test_odds_api.py -v` → Expected : 5 PASS.
Run : `python -m app.collectors.run --help` → Expected : l'aide s'affiche (import OK).

- [ ] **Step 6 : commit**

```bash
git add -A && git commit -m "feat: collecteur The Odds API (5 bookmakers FR + Pinnacle, relevés archivés) et CLI des collecteurs"
```

---

*(Suite : Tasks 7 à 11 — moteur, routes API, paywall, /health, déploiement — dans le fichier `2026-09-10-rushplay-refonte-socle-2.md`.)*
