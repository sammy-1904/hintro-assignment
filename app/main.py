"""
Hintro Meeting Intelligence Service
====================================
FastAPI application entry point.

Startup sequence:
  1. Configure structured logging
  2. Create DB tables (dev convenience — use Alembic in production)
  3. Register middleware (CORS → TraceID)
  4. Register exception handlers
  5. Mount routers
"""

import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.middleware.trace import TraceMiddleware
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.utils.errors import register_exception_handlers

# ── Structured Logging ────────────────────────────────────────────────────────
LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)-8s %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
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
    """Run startup and shutdown logic."""
    logger.info("Starting %s", settings.APP_NAME)
    async with engine.begin() as conn:
        # Create tables that don't exist yet (idempotent)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready")
    yield
    logger.info("Shutting down — disposing DB connections")
    await engine.dispose()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered meeting intelligence service. "
        "Manages meetings, extracts insights from transcripts, "
        "tracks action items, and sends overdue reminders."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (order matters — outermost added last) ─────────────────────────
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
app.include_router(auth_router)
