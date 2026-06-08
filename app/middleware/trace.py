"""
Trace ID middleware.

Reads X-Trace-ID from the incoming request header, or generates a new UUID if
absent. Stores it in a ContextVar so it's accessible from anywhere in the
request lifecycle (loggers, response builders, exception handlers).
"""

import uuid
import logging
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Thread-safe storage for the current request's trace ID
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """Return the trace ID for the current request context."""
    return _trace_id_var.get()


class TraceMiddleware(BaseHTTPMiddleware):
    """Inject a trace ID into every request and attach it to the response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        token = _trace_id_var.set(trace_id)

        logger.info(
            "Request started",
            extra={
                "traceId": trace_id,
                "method": request.method,
                "path": str(request.url.path),
            },
        )

        response: Response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id

        logger.info(
            "Request completed",
            extra={
                "traceId": trace_id,
                "method": request.method,
                "path": str(request.url.path),
                "status": response.status_code,
            },
        )

        _trace_id_var.reset(token)
        return response


class StructuredFormatter(logging.Formatter):
    """
    Format logs as JSON objects containing:
      - timestamp
      - level
      - logger name
      - message
      - traceId (retrieved from current ContextVar)
      - method, path, status, code, detail (if present in extra)
      - exception details (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        import json

        # Retrieve traceId from ContextVar, fallback to record attr, then empty
        trace_id = get_trace_id()
        if not trace_id and hasattr(record, "traceId"):
            trace_id = getattr(record, "traceId")
        if not trace_id:
            trace_id = "N/A"

        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "traceId": trace_id,
        }

        # Include custom request/error details if present
        for key in ["method", "path", "status", "code", "detail"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Include traceback details if an exception occurred
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)
