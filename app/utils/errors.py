"""
Centralised error handling.

AppError is the application's typed exception — raise it anywhere to produce a
clean, structured error response. All unhandled exceptions are caught by the
generic handler so the server never crashes from bad client input.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.middleware.trace import get_trace_id

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Raise this for expected application errors (auth, not found, etc.)."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _error_body(code: str, message: str) -> dict:
    return {
        "traceId": get_trace_id(),
        "success": False,
        "error": {"code": code, "message": message},
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "Application error: %s",
            exc.message,
            extra={"traceId": get_trace_id(), "code": exc.code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Flatten pydantic errors into one readable message
        parts = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err["loc"] if l != "body")
            parts.append(f"{loc}: {err['msg']}" if loc else err["msg"])
        message = "; ".join(parts)

        logger.warning(
            "Validation error",
            extra={"traceId": get_trace_id(), "detail": exc.errors()},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("VALIDATION_ERROR", message),
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error", extra={"traceId": get_trace_id()})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("DATABASE_ERROR", "A database error occurred."),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unexpected error", extra={"traceId": get_trace_id()})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
        )
