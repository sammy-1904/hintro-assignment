import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, JSON_TYPE


class MeetingAnalysis(Base):
    """Stores the AI-generated analysis for a meeting."""

    __tablename__ = "meeting_analyses"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Each field is a JSON list of objects with "citations" arrays
    summary: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    action_items_ai: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    decisions: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    follow_ups: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="analysis")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<MeetingAnalysis meeting_id={self.meeting_id!r}>"
