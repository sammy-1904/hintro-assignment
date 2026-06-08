import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, JSON_TYPE


class ActionItemStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Nullable — action items can be created independently of a meeting
    meeting_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    task: Mapped[str] = mapped_column(String, nullable=False)
    assignee: Mapped[str] = mapped_column(String, nullable=False, index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=ActionItemStatus.PENDING.value, index=True
    )
    citations: Mapped[list] = mapped_column(JSON_TYPE, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="action_items")  # type: ignore[name-defined]
    reminders: Mapped[list["ReminderHistory"]] = relationship(  # type: ignore[name-defined]
        "ReminderHistory", back_populates="action_item", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ActionItem id={self.id!r} task={self.task!r} status={self.status!r}>"
