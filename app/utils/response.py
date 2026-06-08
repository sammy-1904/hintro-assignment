"""
Unified API response helpers.

All responses — success or error — follow the same envelope:
  { "traceId": "...", "success": true/false, "data": {...} }
  { "traceId": "...", "success": false, "error": {"code": "...", "message": "..."} }
"""

from typing import Any

from fastapi.responses import JSONResponse


def success_response(data: Any, trace_id: str, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "traceId": trace_id,
            "success": True,
            "data": data,
        },
    )


def error_response(
    code: str,
    message: str,
    trace_id: str,
    status_code: int = 400,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "traceId": trace_id,
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )
