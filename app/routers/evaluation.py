"""GET /api/evaluation — required evaluation metadata endpoint."""

from fastapi import APIRouter

from app.middleware.trace import get_trace_id
from app.utils.response import success_response

router = APIRouter(tags=["System"])


@router.get("/api/evaluation", summary="Evaluation metadata")
async def evaluation():
    """
    Returns candidate and project metadata for evaluator review.
    Update candidateName, email, and deployedUrl before submission.
    """
    return success_response(
        data={
            "candidateName": "Sameer Rawat",
            "email": "sameerrawat1904@gmail.com",
            "repositoryUrl": "https://github.com/sammy-1904/hintro-assignment",
            "deployedUrl": "https://hintro-assignment-emb9.onrender.com",
            "externalIntegration": "Email via Resend (https://resend.com)",
            "features": [
                "JWT Authentication (register + login)",
                "Meeting Management (CRUD + pagination)",
                "AI Analysis via Gemini 3.5 Flash (grounded + citations)",
                "Hallucination prevention (prompt grounding + citation validation)",
                "Action Item Management (CRUD + status tracking)",
                "Overdue Detection (GET /api/action-items/overdue)",
                "Scheduled Reminder Job (APScheduler, configurable interval)",
                "Email Reminders via Resend (real third-party integration)",
                "Unified API response format (traceId + success + data/error)",
                "Request trace ID middleware",
                "Structured logging",
                "Global error handling",
                "Input validation (Pydantic)",
                "OpenAPI/Swagger docs at /docs",
                "Docker support",
            ],
        },
        trace_id=get_trace_id(),
    )
