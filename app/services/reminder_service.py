"""
Email reminder service using Resend (https://resend.com).

Resend was chosen because:
  - Simple REST API with an official Python SDK
  - Free tier (100 emails/day) sufficient for evaluation
  - No SMTP configuration needed
  - Reliable delivery with webhook support
"""

import logging

import resend

from app.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


def send_overdue_reminder(
    to_email: str,
    task: str,
    assignee: str,
    due_date: str,
    action_item_id: str,
) -> dict:
    """
    Send an overdue action item reminder via Resend email.

    Returns {"success": True, "id": "..."} or {"success": False, "error": "..."}.
    """
    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #e53e3e;">⏰ Overdue Action Item Reminder</h2>
      <p>The following action item is overdue and requires your attention:</p>
      <table style="border-collapse: collapse; width: 100%;">
        <tr>
          <td style="padding: 8px; font-weight: bold; background: #f7fafc;">Task</td>
          <td style="padding: 8px; border: 1px solid #e2e8f0;">{task}</td>
        </tr>
        <tr>
          <td style="padding: 8px; font-weight: bold; background: #f7fafc;">Assigned To</td>
          <td style="padding: 8px; border: 1px solid #e2e8f0;">{assignee}</td>
        </tr>
        <tr>
          <td style="padding: 8px; font-weight: bold; background: #f7fafc;">Due Date</td>
          <td style="padding: 8px; border: 1px solid #e2e8f0; color: #e53e3e;">{due_date}</td>
        </tr>
      </table>
      <p style="margin-top: 16px; color: #718096; font-size: 14px;">
        Action Item ID: {action_item_id}
      </p>
    </div>
    """

    try:
        response = resend.Emails.send(
            {
                "from": settings.REMINDER_FROM_EMAIL,
                "to": [to_email],
                "subject": f"[Overdue] Action Item: {task}",
                "html": html_body,
            }
        )
        email_id = response.get("id", "unknown")
        logger.info(
            "Reminder email sent to %s for action item %s (email_id=%s)",
            to_email,
            action_item_id,
            email_id,
        )
        return {"success": True, "id": email_id}

    except Exception as exc:
        logger.error(
            "Failed to send reminder to %s for action item %s: %s",
            to_email,
            action_item_id,
            str(exc),
        )
        return {"success": False, "error": str(exc)}
