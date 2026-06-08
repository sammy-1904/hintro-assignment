"""
Hintro Meeting Intelligence Service (Reloaded for .env change)
====================================
FastAPI application entry point.

Startup sequence:
  1. Configure structured logging
  2. Import all models (ensures create_all sees every table)
  3. Create DB tables
  4. Start background scheduler (overdue action item reminders)
  5. Register middleware: CORS → TraceID
  6. Register global exception handlers
  7. Mount all routers
"""

import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine

# Import all models so Base.metadata.create_all() knows about every table
import app.models  # noqa: F401

from app.middleware.trace import TraceMiddleware
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.meetings import router as meetings_router
from app.routers.action_items import router as action_items_router
from app.routers.evaluation import router as evaluation_router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.utils.errors import register_exception_handlers

# ── Logging ───────────────────────────────────────────────────────────────────

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": "app.middleware.trace.StructuredFormatter",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "DEBUG" if settings.DEBUG else "INFO",
        "handlers": ["console"],
    },
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.APP_NAME)

    # Create all DB tables (idempotent — safe to run on every startup)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    # Start background reminder scheduler
    start_scheduler()

    yield  # ← Server is running

    # Shutdown
    stop_scheduler()
    await engine.dispose()
    logger.info("Shutdown complete")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered meeting intelligence service. Manages meetings, extracts "
        "grounded insights from transcripts, tracks action items, and sends "
        "overdue reminders via email."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
# Note: add_middleware registers in LIFO order (last added = outermost = runs first).
# We want: TraceMiddleware → CORSMiddleware → route handler
# So add CORS first (inner), then Trace (outer).

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TraceMiddleware)

# ── Exception Handlers ────────────────────────────────────────────────────────

register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(evaluation_router)
app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(action_items_router)
