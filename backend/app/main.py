import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import setup_logging

# Ensure ORM models are imported before create_all
from app import models  # noqa: F401

setup_logging()
log = logging.getLogger("rushplay")

HEARTBEATS = Path(__file__).resolve().parents[1] / "heartbeats"
STALE_AFTER = {"fd_uk": timedelta(days=8), "fd_org": timedelta(hours=36), "odds": timedelta(hours=36)}
LEGAL_NOTICE = {
    "warning": "Les paris sportifs comportent des risques : endettement, dépendance… Appelez le 09 74 75 13 13 (appel non surtaxé).",
    "minimum_age": 18,
    "positioning": "Nous ne prédisons pas. Nous vous montrons ce que le marché pense, et où il se contredit.",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Permet aux tests (DB mockée) de sauter l'initialisation qui se connecte à
    # Postgres. En production la variable n'est pas définie et l'init a lieu.
    if os.getenv("RUSHPLAY_SKIP_DB_INIT") != "1":
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as exc:
            log.warning("Database initialization skipped: %s", exc)
    yield


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception):
    log.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"success": False, "message": "Internal server error"})


def _collectors_status() -> dict:
    out = {}
    now = datetime.now(timezone.utc)
    for name, max_age in STALE_AFTER.items():
        f = HEARTBEATS / f"{name}.json"
        if not f.exists():
            out[name] = {"at": None, "stale": True}
            continue
        at = datetime.fromisoformat(json.loads(f.read_text(encoding="utf-8"))["at"])
        out[name] = {"at": at.isoformat(), "stale": now - at > max_age}
    return out


@app.get("/health")
def health():
    return {"success": True, "message": "API healthy", "data": {"env": settings.env, "collectors": _collectors_status()}}


@app.get("/api/v1/legal")
def legal():
    return {"success": True, "message": "Legal notice", "data": LEGAL_NOTICE}


app.include_router(api_router, prefix="/api/v1")
