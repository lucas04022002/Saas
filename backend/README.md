# RushPlay Backend (FastAPI)

Lecture du marché des paris sportifs : favori, probabilité de référence,
écarts entre bookmakers, mouvements de cotes, carnet de bankroll. Pas de
prédiction, pas de machine learning.

## Lancement local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # renseigner les variables ci-dessous
uvicorn app.main:app --reload --port 8000
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `DATABASE_URL` | URL Postgres (`postgresql+psycopg://…`) ou SQLite (`sqlite:///./dev.db`) pour le développement local |
| `JWT_SECRET` | secret de signature des jetons (≥ 16 caractères) |
| `JWT_ALGORITHM` | algorithme JWT (défaut `HS256`) |
| `JWT_EXPIRE_MINUTES` | durée de validité du jeton en minutes (défaut `60`) |
| `CRON_SECRET` | secret des tâches planifiées (≥ 16 caractères) |
| `CORS_ORIGINS` | origines autorisées, séparées par des virgules |
| `THE_ODDS_API_KEY` | clé The Odds API (relevés de cotes) |
| `FOOTBALL_DATA_ORG_KEY` | clé football-data.org (calendrier, résultats) |
| `FD_UK_BASE_URL` | base URL football-data.co.uk (défaut fourni) |
| `ENV` | `development` ou `production` |

### Développement local avec SQLite

Pour le développement du frontend sans Postgres, utilisez SQLite avec une base de données locale vide :

```bash
DATABASE_URL=sqlite:///./dev.db python -m uvicorn app.main:app --port 8000
```

Les tables sont créées automatiquement au démarrage (n'omettez pas `RUSHPLAY_SKIP_DB_INIT` lors du premier lancement).

## Collecteurs

```bash
python -m app.collectors.run seed                          # alias équipes
python -m app.collectors.run fd_uk --seasons 2324 2425 2526 # historique + cotes ouverture/clôture
python -m app.collectors.run fd_org                         # calendrier, résultats, règlement des paris
python -m app.collectors.run odds                           # relevé de cotes (The Odds API)
```

Chaque run réussi écrit un heartbeat dans `backend/heartbeats/<nom>.json`,
lu par `/health`.

## Tests

```bash
python -m pytest -q
```

## Routes principales

| Route | Description |
|---|---|
| `GET /health` | santé de l'API + fraîcheur des collecteurs |
| `GET /api/v1/legal` | mentions légales ANJ, âge minimum, positionnement |
| `POST /api/v1/auth/signup` | inscription (18 ans ou plus obligatoire) |
| `POST /api/v1/auth/login` | connexion |
| `GET /api/v1/auth/me` | utilisateur courant |
| `GET /api/v1/matches` | matchs à venir / du jour |
| `GET /api/v1/matches/{id}` | détail d'un match (probabilités, écarts, mouvement) |
| `GET /api/v1/books` | comparateur par bookmaker (abonnement Pro) |
| `GET /api/v1/bankroll` | carnet de paris de l'utilisateur |
| `POST /api/v1/bankroll` | enregistrer un pari |
| `DELETE /api/v1/bankroll/{id}` | supprimer un pari |
| `POST /api/v1/bankroll/{id}/void` | annuler un pari (remboursé, non réglé) |
| `GET /api/v1/track-record` | historique public du favori vs résultat réel |

## Déploiement

Voir [`deploy/coolify.md`](../deploy/coolify.md) (VPS Hetzner + Coolify) et
[`deploy/crontab.txt`](../deploy/crontab.txt) pour la planification des
collecteurs.
