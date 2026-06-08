import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReminderHistory(Base):
    """Audit log of every reminder notification sent."""

    __tablename__ = "reminder_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    action_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("action_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String, nullable=False, default="email")
    recipient: Mapped[str] = mapped_column(String, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    action_item: Mapped["ActionItem"] = relationship(  # type: ignore[name-defined]
        "ActionItem", back_populates="reminders"
    )

    def __repr__(self) -> str:
        return f"<ReminderHistory action_item_id={self.action_item_id!r} success={self.success!r}>"
