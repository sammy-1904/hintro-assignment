"""
Background scheduler — detects overdue action items and sends email reminders.

Uses APScheduler's AsyncIOScheduler so it runs on the same event loop as
FastAPI without blocking the server.

Job flow:
  1. Query all action items where status != COMPLETED AND due_date < now
  2. For each: send an email via Resend
  3. Record the attempt in reminder_history (success or failure)
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.action_item import ActionItem, ActionItemStatus
from app.models.reminder_history import ReminderHistory
from app.services.reminder_service import send_overdue_reminder

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def _run_overdue_check() -> None:
    """Core job function — runs on each scheduler tick."""
    logger.info("Scheduler: starting overdue action item check")

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(ActionItem).where(
                ActionItem.status != ActionItemStatus.COMPLETED.value,
                ActionItem.due_date < now,
            )
        )
        overdue_items = result.scalars().all()

        logger.info("Scheduler: found %d overdue action items", len(overdue_items))

        for item in overdue_items:
            # Use assignee as the recipient — if it looks like an email, send to it.
            # In a real system you'd resolve user email from your users table.
            recipient = item.assignee
            if "@" not in recipient:
                logger.warning(
                    "Assignee '%s' for action item %s is not an email — skipping",
                    recipient,
                    item.id,
                )
                continue

            result_info = send_overdue_reminder(
                to_email=recipient,
                task=item.task,
                assignee=item.assignee,
                due_date=item.due_date.strftime("%Y-%m-%d"),
                action_item_id=item.id,
            )

            # Always record the attempt — success or failure
            history = ReminderHistory(
                action_item_id=item.id,
                channel="email",
                recipient=recipient,
                success=result_info["success"],
                error_message=result_info.get("error"),
            )
            db.add(history)

        await db.commit()
        logger.info("Scheduler: overdue check complete")


def start_scheduler() -> None:
    """Register the job and start the scheduler. Called on app startup."""
    scheduler.add_job(
        _run_overdue_check,
        trigger="interval",
        hours=settings.REMINDER_INTERVAL_HOURS,
        id="overdue_reminder_job",
        replace_existing=True,
        misfire_grace_time=300,  # allow 5-min late start (e.g. after server restart)
    )
    scheduler.start()
    logger.info(
        "Scheduler started — overdue check every %d hour(s)",
        settings.REMINDER_INTERVAL_HOURS,
    )


def stop_scheduler() -> None:
    """Graceful shutdown. Called on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
