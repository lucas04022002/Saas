# Dockerfile de déploiement (Koyeb / Fly / tout hébergeur Docker).
# Contexte de build = racine du repo, car le moteur de prédiction charge ses
# fichiers modèle (prediction_engine.py, xgboost_model.pkl, elo_ratings.json,
# team_stats.json, draw_thresholds_by_league.json) depuis la racine.
FROM python:3.12-slim

WORKDIR /app

# Dépendances d'abord (cache Docker)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Code + fichiers modèle (le .dockerignore exclut frontend, caches, backtests…)
COPY . .

WORKDIR /app/backend

# La racine du repo contient les fichiers modèle
ENV PREDICTION_MODEL_ROOT=/app
ENV PYTHONUNBUFFERED=1
ENV ENV=production
ENV PREDICTION_PROVIDER=local

EXPOSE 8000

# Koyeb/Render fournissent $PORT ; défaut 8000 en local.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
