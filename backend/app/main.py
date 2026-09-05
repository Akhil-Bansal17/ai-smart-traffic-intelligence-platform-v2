"""
FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --app-dir backend
(or from inside backend/:  uvicorn app.main:app --reload)
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up in '%s' environment", settings.environment)
    try:
        from app.db.base import Base
        from app.db.session import engine
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema synchronized")
    except Exception as err:
        logger.warning("Database schema synchronization skipped: %s", err)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="AI Smart Traffic Intelligence Platform API",
    version="0.1.0",
    description="Traffic video analysis, analytics, prediction, and decision-support simulations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["system"])
def root_health() -> dict:
    """Unversioned liveness check for infra (load balancers, Docker healthchecks)."""
    return {"status": "ok", "service": "traffic-platform-api"}
