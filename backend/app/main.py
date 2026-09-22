import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.client_ip import client_ip, limiter
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




async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.detail})


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
        try:
            at = datetime.fromisoformat(json.loads(f.read_text(encoding="utf-8"))["at"])
            # Handle naive datetime by treating as UTC
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            out[name] = {"at": at.isoformat(), "stale": now - at > max_age}
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            log.warning("heartbeat illisible pour %s : %s", name, exc)
            out[name] = {"at": None, "stale": True}
    return out


def health():
    return {"success": True, "message": "API healthy", "data": {"env": settings.env, "collectors": _collectors_status()}}


def legal():
    return {"success": True, "message": "Legal notice", "data": LEGAL_NOTICE}


SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Les réponses sont personnalisées (plan, quota, carnet) : aucun proxy ne doit les garder.
    "Cache-Control": "no-store",
}


async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


def whoami(request: Request):
    """L'adresse que l'API attribue à l'appelant : la seule preuve directe que le proxy est bien lu.
    Elle ne révèle à l'appelant que sa propre adresse."""
    return {"success": True, "message": "", "data": {"ip": client_ip(request)}}


def create_app() -> FastAPI:
    """L'application, assemblée d'après `settings` — une fabrique, pour que les tests puissent
    construire une instance de production sans redémarrer le processus.

    En production la documentation interactive est fermée : `/docs` répondait 200 sur
    `api.rushplay.fr` et décrivait toute la surface, webhook compris (audit du 22/09/2026).
    """
    en_production = settings.env == "production"
    application = FastAPI(
        title=settings.app_name, version="0.1.0", lifespan=lifespan,
        docs_url=None if en_production else "/docs",
        redoc_url=None if en_production else "/redoc",
        openapi_url=None if en_production else "/openapi.json",
    )
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.middleware("http")(security_headers)
    application.exception_handler(HTTPException)(http_exception_handler)
    application.exception_handler(Exception)(generic_exception_handler)
    application.get("/health")(health)
    application.get("/api/v1/legal")(legal)
    application.get("/api/v1/whoami")(whoami)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
