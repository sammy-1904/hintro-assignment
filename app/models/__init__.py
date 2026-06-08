# Import all models here so Base.metadata.create_all() picks up every table.
from app.models.user import User
from app.models.meeting import Meeting
from app.models.meeting_analysis import MeetingAnalysis
from app.models.action_item import ActionItem, ActionItemStatus
from app.models.reminder_history import ReminderHistory

__all__ = [
    "User",
    "Meeting",
    "MeetingAnalysis",
    "ActionItem",
    "ActionItemStatus",
    "ReminderHistory",
]
