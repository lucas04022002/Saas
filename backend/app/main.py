import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.client_ip import client_ip, limiter
from app.api.deps import get_db
from app.core.config import settings
from app.models.collector_heartbeat import CollectorHeartbeat
from app.core.database import Base, engine
from app.core.logging import setup_logging

# Ensure ORM models are imported before create_all
from app import models  # noqa: F401

setup_logging()
log = logging.getLogger("rushplay")

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




async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    # Couvre aussi les 404 de routes inconnues (Starlette), qui sortaient en `{"detail": "Not Found"}`.
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.detail, "data": None})


async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Un 422 dans l'enveloppe, avec le premier message lisible — pas la forme brute de FastAPI ni
    l'expression régulière complète du paramètre (audit du 22/09/2026, F2)."""
    erreurs = exc.errors() or []
    premier = erreurs[0] if erreurs else {}
    champ = ".".join(str(x) for x in premier.get("loc", ()) if x not in ("body", "query", "path"))
    msg = str(premier.get("msg", "Requête invalide")).replace("Value error, ", "")
    message = f"{champ} : {msg}" if champ and champ not in msg else msg
    return JSONResponse(status_code=422, content={"success": False, "message": message, "data": None})


async def generic_exception_handler(_: Request, exc: Exception):
    log.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"success": False, "message": "Internal server error", "data": None})


def _collectors_status(db: Session) -> dict:
    out = {}
    now = datetime.now(timezone.utc)
    lus = {h.name: h.at for h in db.scalars(select(CollectorHeartbeat)).all()}
    for name, max_age in STALE_AFTER.items():
        at = lus.get(name)
        if at is None:
            out[name] = {"at": None, "stale": True}
            continue
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        out[name] = {"at": at.isoformat(), "stale": now - at > max_age}
    return out


def health(db: Session = Depends(get_db)):
    return {"success": True, "message": "API healthy", "data": {"env": settings.env, "collectors": _collectors_status(db)}}


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
    application.exception_handler(StarletteHTTPException)(http_exception_handler)
    application.exception_handler(RequestValidationError)(validation_exception_handler)
    application.exception_handler(Exception)(generic_exception_handler)
    application.get("/health")(health)
    application.get("/api/v1/legal")(legal)
    application.get("/api/v1/whoami")(whoami)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
