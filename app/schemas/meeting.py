from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ── Transcript ────────────────────────────────────────────────────────────────

class TranscriptEntry(BaseModel):
    timestamp: str  # e.g. "00:10", "01:25"
    speaker: str
    text: str

    @field_validator("timestamp")
    @classmethod
    def timestamp_format(cls, v: str) -> str:
        # Accept HH:MM or MM:SS — just ensure it's non-empty
        if not v.strip():
            raise ValueError("Timestamp cannot be empty")
        return v.strip()

    @field_validator("speaker", "text")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


# ── Request ───────────────────────────────────────────────────────────────────

class MeetingCreate(BaseModel):
    title: str
    participants: List[EmailStr]
    meetingDate: datetime          # camelCase to match assignment example
    transcript: List[TranscriptEntry]

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Meeting title is required")
        return v.strip()

    @field_validator("participants")
    @classmethod
    def at_least_one_participant(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one participant is required")
        return v

    @field_validator("transcript")
    @classmethod
    def transcript_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("Transcript cannot be empty")
        return v


# ── Response ──────────────────────────────────────────────────────────────────

class MeetingAnalysisResponse(BaseModel):
    summary: List[dict]
    actionItems: List[dict]
    decisions: List[dict]
    followUps: List[dict]

    @classmethod
    def from_orm_analysis(cls, a: object) -> "MeetingAnalysisResponse":
        if not a:
            return None
        return cls(
            summary=a.summary,
            actionItems=a.action_items_ai,
            decisions=a.decisions,
            followUps=a.follow_ups,
        )


class MeetingResponse(BaseModel):
    id: str
    title: str
    participants: List[str]
    meetingDate: datetime
    transcript: List[dict]
    createdAt: datetime
    analysis: Optional[MeetingAnalysisResponse] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

    @classmethod
    def from_orm_meeting(cls, m: object) -> "MeetingResponse":
        analysis_data = None
        try:
            if getattr(m, "analysis", None) is not None:
                analysis_data = MeetingAnalysisResponse.from_orm_analysis(m.analysis)
        except Exception:
            pass

        return cls(
            id=m.id,
            title=m.title,
            participants=m.participants,
            meetingDate=m.meeting_date,
            transcript=m.transcript,
            createdAt=m.created_at,
            analysis=analysis_data,
        )


# ── Citation (shared) ─────────────────────────────────────────────────────────

class Citation(BaseModel):
    timestamp: str


# ── AI Analysis Response ──────────────────────────────────────────────────────

class CitedSummary(BaseModel):
    text: str
    citations: List[Citation]


class CitedActionItem(BaseModel):
    task: str
    assignee: str
    citations: List[Citation]


class CitedDecision(BaseModel):
    decision: str
    citations: List[Citation]


class CitedFollowUp(BaseModel):
    suggestion: str
    citations: List[Citation]


class AnalysisResponse(BaseModel):
    meetingId: str
    summary: List[CitedSummary]
    actionItems: List[CitedActionItem]
    decisions: List[CitedDecision]
    followUps: List[CitedFollowUp]
