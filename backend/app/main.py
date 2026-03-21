import logging

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
from app.core.runtime_migrations import ensure_runtime_columns
from app.services.prediction_service import prediction_service

# Ensure ORM models are imported before create_all
from app import models  # noqa: F401

setup_logging()
log = logging.getLogger("rushplay")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.app_name, version="0.1.0")
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


@app.on_event("startup")
def startup_event():
    try:
        ensure_runtime_columns(engine)
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        # Keep API alive for non-DB endpoints (health/prediction) until DB is configured.
        log.warning("Database initialization skipped: %s", exc)


@app.get("/health")
def health():
    return {
        "success": True,
        "message": "API healthy",
        "data": {"env": settings.env, "prediction_provider": prediction_service.health()},
    }


app.include_router(api_router, prefix="/api/v1")
