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
        from app.db.session import SessionLocal, engine
        from app.services.cv.job_manager import get_analysis_job_manager

        Base.metadata.create_all(bind=engine)
        logger.info("Database schema synchronized")

        # Phase 17: Recover any stale RUNNING jobs left from prior process crash
        startup_db = SessionLocal()
        try:
            manager = get_analysis_job_manager()
            manager.recover_stale_jobs(startup_db)
        finally:
            startup_db.close()
    except Exception as err:
        logger.warning("Database schema synchronization / startup recovery skipped: %s", err)

    yield

    logger.info("Shutting down")
    try:
        from app.services.cv.job_manager import get_analysis_job_manager
        get_analysis_job_manager().shutdown(wait=False)
    except Exception as err:
        logger.warning("Job manager shutdown error: %s", err)


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


@app.get("/readiness", tags=["system"])
def root_readiness():
    """Unversioned readiness check for container orchestrators (Kubernetes, Docker)."""
    from app.api.v1.health import readiness as check_readiness
    from app.db.session import SessionLocal
    from fastapi import Response
    resp = Response()
    db = SessionLocal()
    try:
        return check_readiness(response=resp, db=db)
    finally:
        db.close()

