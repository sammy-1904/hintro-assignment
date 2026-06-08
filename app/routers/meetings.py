"""
Meetings router.

POST   /api/meetings              — create meeting
GET    /api/meetings              — list meetings (paginated)
GET    /api/meetings/:id          — get single meeting
POST   /api/meetings/:id/analyze  — AI analysis with transcript citations
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.trace import get_trace_id
from app.models.meeting import Meeting
from app.models.meeting_analysis import MeetingAnalysis
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingResponse
from app.services.ai_service import analyze_transcript
from app.utils.errors import AppError
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])


# ── Create ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    status_code=201,
    summary="Create a new meeting",
    description="Store meeting details and transcript. Returns the created meeting.",
)
async def create_meeting(
    body: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = Meeting(
        user_id=user.id,
        title=body.title,
        participants=[str(p) for p in body.participants],
        meeting_date=body.meetingDate,
        transcript=[t.model_dump() for t in body.transcript],
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    logger.info("Meeting created: %s by user %s", meeting.id, user.id,
                extra={"traceId": get_trace_id()})

    return success_response(
        data=MeetingResponse.from_orm_meeting(meeting).model_dump(),
        trace_id=get_trace_id(),
        status_code=201,
    )


# ── List ──────────────────────────────────────────────────────────────────────


@router.get(
    "",
    summary="List meetings",
    description="Returns paginated list of meetings for the authenticated user.",
)
async def list_meetings(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    base_query = select(Meeting).where(Meeting.user_id == user.id)

    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(Meeting.analysis))
        .order_by(Meeting.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    meetings = result.scalars().all()

    return success_response(
        data={
            "meetings": [MeetingResponse.from_orm_meeting(m).model_dump() for m in meetings],
            "total": total,
            "page": page,
            "perPage": per_page,
        },
        trace_id=get_trace_id(),
    )


# ── Get One ───────────────────────────────────────────────────────────────────


@router.get(
    "/{meeting_id}",
    summary="Get a meeting by ID",
)
async def get_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.analysis))
        .where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    )
    meeting = result.scalar_one_or_none()
    if meeting is None:
        raise AppError("MEETING_NOT_FOUND", "Meeting not found.", 404)

    return success_response(
        data=MeetingResponse.from_orm_meeting(meeting).model_dump(),
        trace_id=get_trace_id(),
    )


# ── Analyze ───────────────────────────────────────────────────────────────────


@router.post(
    "/{meeting_id}/analyze",
    summary="Analyze meeting with AI",
    description=(
        "Sends the meeting transcript to Gemini. Returns a grounded analysis "
        "with citations referencing actual transcript timestamps. "
        "Re-analyzing a meeting overwrites the previous result."
    ),
)
async def analyze_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Fetch meeting (and verify ownership)
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    )
    meeting = result.scalar_one_or_none()
    if meeting is None:
        raise AppError("MEETING_NOT_FOUND", "Meeting not found.", 404)

    if not meeting.transcript:
        raise AppError("EMPTY_TRANSCRIPT", "Meeting has no transcript to analyze.", 422)

    logger.info("Starting AI analysis for meeting %s", meeting_id,
                extra={"traceId": get_trace_id()})

    # Call Gemini (may raise AppError on failure)
    analysis_data = await analyze_transcript(meeting.transcript, meeting.participants)

    # Upsert analysis — overwrite if already exists
    existing_result = await db.execute(
        select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting_id)
    )
    analysis = existing_result.scalar_one_or_none()

    if analysis:
        analysis.summary = analysis_data["summary"]
        analysis.action_items_ai = analysis_data["actionItems"]
        analysis.decisions = analysis_data["decisions"]
        analysis.follow_ups = analysis_data["followUps"]
    else:
        analysis = MeetingAnalysis(
            meeting_id=meeting_id,
            summary=analysis_data["summary"],
            action_items_ai=analysis_data["actionItems"],
            decisions=analysis_data["decisions"],
            follow_ups=analysis_data["followUps"],
        )
        db.add(analysis)

    # ── Automatically create Action Items in DB ──────────────────────────────────
    from app.models.action_item import ActionItem
    from datetime import datetime, timedelta, timezone

    default_due_date = meeting.meeting_date + timedelta(days=7)

    existing_items_result = await db.execute(
        select(ActionItem).where(ActionItem.meeting_id == meeting_id)
    )
    existing_items = existing_items_result.scalars().all()
    existing_tasks = {item.task: item for item in existing_items}

    for ai_item in analysis_data.get("actionItems", []):
        task_text = ai_item.get("task", "").strip()
        assignee = ai_item.get("assignee", "").strip()
        citations = ai_item.get("citations", [])
        
        if not task_text or not assignee:
            continue
            
        if task_text in existing_tasks:
            item = existing_tasks[task_text]
            item.assignee = assignee
            item.citations = citations
        else:
            new_item = ActionItem(
                meeting_id=meeting_id,
                task=task_text,
                assignee=assignee,
                due_date=default_due_date,
                citations=citations,
            )
            db.add(new_item)

    await db.commit()
    await db.refresh(analysis)

    logger.info("AI analysis saved for meeting %s", meeting_id,
                extra={"traceId": get_trace_id()})

    return success_response(
        data={
            "meetingId": meeting_id,
            "summary": analysis.summary,
            "actionItems": analysis.action_items_ai,
            "decisions": analysis.decisions,
            "followUps": analysis.follow_ups,
        },
        trace_id=get_trace_id(),
    )
