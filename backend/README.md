# RushPlay Backend (FastAPI)

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Database (Supabase)

1. Create a Supabase project.
2. Copy the pooled Postgres URL.
3. Set `DATABASE_URL` in `.env`.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Seed demo data

```bash
python seed.py
```

## Main routes

- `GET /health`
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/matches`
- `GET /api/v1/opportunities`
- `POST /api/v1/predictions/match`
- `POST /api/v1/analyses/run-all`
- `POST /api/v1/cron/daily-run` (requires header `X-CRON-KEY`)

## Prediction provider

- `PREDICTION_PROVIDER=local` => branch directly on local Python model (`prediction_engine.py`)
- `PREDICTION_PROVIDER=mock` => mock response

## Cron test example

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/cron/daily-run?limit=5" \
  -H "X-CRON-KEY: change-me-cron"
```

## Daily automation (macOS launchd)

Installed agent label: `com.rushplay.dailyrun`

- Runs every day at `08:00`
- Calls `POST /api/v1/cron/daily-run?limit=50`
- Uses `CRON_SECRET` from `.env` captured at install time

Useful commands:

```bash
launchctl print "gui/$(id -u)/com.rushplay.dailyrun"
launchctl kickstart -k "gui/$(id -u)/com.rushplay.dailyrun"
```

## Deploy 24/7 (Render + Supabase)

The repo includes a Render blueprint: [`render.yaml`](../render.yaml).

### 1. Push code to GitHub

Push the full project (not only `backend/`) so model files are available:
- `prediction_engine.py`
- `xgboost_model.pkl`
- `team_stats.json`

### 2. Create services on Render

In Render:
- New + Blueprint
- Select your repository
- Render reads `render.yaml` and creates:
  - `rushplay-api` (web service)
  - `rushplay-daily-analysis` (cron job)

### 3. Set required env vars on Render

For both services:
- `DATABASE_URL` (Supabase connection string)
- `JWT_SECRET` (strong secret)
- `CRON_SECRET` (strong secret)
- `CORS_ORIGINS` (your frontend URL)

Defaults already configured in blueprint:
- `PREDICTION_PROVIDER=local`
- `PREDICTION_MODEL_ROOT=/opt/render/project/src`

### 4. Post-deploy checks

- Open `https://<your-api-domain>/health`
- Verify:
  - `success=true`
  - `prediction_provider.provider=local_python`

### Notes

- Render cron uses `scripts/daily_run.py` directly (does not require your local Mac).
- Existing local `launchd` automation can be kept for local dev, but cloud cron is the 24/7 source.
