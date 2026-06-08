"""
Action Items router.

POST   /api/action-items              — create action item
GET    /api/action-items              — list with filters (status, assignee, meetingId)
GET    /api/action-items/overdue      — get all overdue items
PATCH  /api/action-items/:id/status  — update status

IMPORTANT: /overdue must be declared BEFORE /:id so FastAPI doesn't try to
match the literal string "overdue" as an item ID.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.trace import get_trace_id
from app.models.action_item import ActionItem, ActionItemStatus
from app.models.user import User
from app.schemas.action_item import ActionItemCreate, ActionItemResponse, StatusUpdate
from app.utils.errors import AppError
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/action-items", tags=["Action Items"])


@router.post(
    "/trigger-reminders",
    summary="Trigger overdue reminders check",
    description="Manually trigger the background overdue check and send pending reminder emails immediately.",
)
async def trigger_reminders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.scheduler import _run_overdue_check
    await _run_overdue_check()
    return success_response(
        data={"message": "Overdue check completed. Check terminal logs for email delivery status."},
        trace_id=get_trace_id(),
    )


# ── Create ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    status_code=201,
    summary="Create an action item",
    description="Create a standalone action item, optionally linked to a meeting.",
)
async def create_action_item(
    body: ActionItemCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = ActionItem(
        meeting_id=body.meetingId,
        task=body.task,
        assignee=body.assignee,
        due_date=body.dueDate,
        citations=[c.model_dump() for c in body.citations],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    logger.info("Action item created: %s", item.id, extra={"traceId": get_trace_id()})

    return success_response(
        data=ActionItemResponse.from_orm_item(item).model_dump(),
        trace_id=get_trace_id(),
        status_code=201,
    )


# ── List (with filters) ───────────────────────────────────────────────────────


@router.get(
    "",
    summary="List action items",
    description="Filter by status, assignee, and/or meetingId. Supports pagination.",
)
async def list_action_items(
    status: str | None = Query(None, description="Filter by status (PENDING, IN_PROGRESS, COMPLETED)"),
    assignee: str | None = Query(None, description="Filter by assignee name or email"),
    meetingId: str | None = Query(None, description="Filter by meeting ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conditions = []

    if status:
        valid = [s.value for s in ActionItemStatus]
        if status not in valid:
            raise AppError("INVALID_STATUS", f"Status must be one of: {', '.join(valid)}", 400)
        conditions.append(ActionItem.status == status)

    if assignee:
        conditions.append(ActionItem.assignee.ilike(f"%{assignee}%"))

    if meetingId:
        conditions.append(ActionItem.meeting_id == meetingId)

    query = select(ActionItem)
    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(
        query.order_by(ActionItem.due_date.asc()).offset((page - 1) * per_page).limit(per_page)
    )
    items = result.scalars().all()

    return success_response(
        data=[ActionItemResponse.from_orm_item(i).model_dump() for i in items],
        trace_id=get_trace_id(),
    )


# ── Overdue (MUST be before /{item_id}) ──────────────────────────────────────


@router.get(
    "/overdue",
    summary="Get overdue action items",
    description=(
        "Returns all action items where status != COMPLETED AND dueDate < now. "
        "These are the items the reminder scheduler will notify about."
    ),
)
async def get_overdue_items(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ActionItem).where(
            ActionItem.status != ActionItemStatus.COMPLETED.value,
            ActionItem.due_date < now,
        ).order_by(ActionItem.due_date.asc())
    )
    items = result.scalars().all()

    return success_response(
        data=[ActionItemResponse.from_orm_item(i).model_dump() for i in items],
        trace_id=get_trace_id(),
    )


# ── Update Status ─────────────────────────────────────────────────────────────


@router.patch(
    "/{item_id}/status",
    summary="Update action item status",
    description="Update the status of an action item to PENDING, IN_PROGRESS, or COMPLETED.",
)
async def update_status(
    item_id: str,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(ActionItem).where(ActionItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise AppError("ACTION_ITEM_NOT_FOUND", "Action item not found.", 404)

    item.status = body.status
    item.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(item)

    logger.info("Action item %s status → %s", item_id, body.status,
                extra={"traceId": get_trace_id()})

    return success_response(
        data=ActionItemResponse.from_orm_item(item).model_dump(),
        trace_id=get_trace_id(),
    )
