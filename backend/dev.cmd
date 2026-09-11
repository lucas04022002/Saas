@echo off
rem Lance l'API RushPlay en local sur SQLite (base de demo dev.db). Usage : backend\dev.cmd
cd /d "%~dp0"
set "JWT_SECRET=test-secret-key-for-pytest-only-32chars"
set "CRON_SECRET=test-cron-secret-key-for-pytest-32chars"
set "DATABASE_URL=sqlite:///./dev.db"
set "CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
