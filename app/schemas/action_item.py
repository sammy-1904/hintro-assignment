from datetime import datetime
from typing import List

from pydantic import BaseModel, field_validator

from app.models.action_item import ActionItemStatus


# ── Request ───────────────────────────────────────────────────────────────────

class Citation(BaseModel):
    timestamp: str


class ActionItemCreate(BaseModel):
    task: str
    assignee: str
    dueDate: datetime
    meetingId: str | None = None
    citations: List[Citation] = []

    @field_validator("task", "assignee")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        valid = [s.value for s in ActionItemStatus]
        if v not in valid:
            raise ValueError(f"Status must be one of: {', '.join(valid)}")
        return v


# ── Response ──────────────────────────────────────────────────────────────────

class ActionItemResponse(BaseModel):
    id: str
    meetingId: str | None
    task: str
    assignee: str
    dueDate: datetime
    status: str
    citations: List[dict]
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def from_orm_item(cls, item: object) -> "ActionItemResponse":
        return cls(
            id=item.id,
            meetingId=item.meeting_id,
            task=item.task,
            assignee=item.assignee,
            dueDate=item.due_date,
            status=item.status,
            citations=item.citations,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
