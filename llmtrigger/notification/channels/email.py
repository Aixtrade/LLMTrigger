"""Email notification channel."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from llmtrigger.core.config import get_settings
from llmtrigger.core.logging import get_logger
from llmtrigger.models.notification import NotificationTask
from llmtrigger.models.rule import NotifyTarget
from llmtrigger.notification.channels.base import NotificationChannel

logger = get_logger(__name__)


class EmailChannel(NotificationChannel):
    """Email notification channel using SMTP."""

    def __init__(self):
        """Initialize with settings."""
        self._settings = get_settings()

    @property
    def channel_type(self) -> str:
        return "email"

    async def send(self, target: NotifyTarget, task: NotificationTask) -> bool:
        """Send email notification.

        Args:
            target: Target with email recipients
            task: Notification task

        Returns:
            True if sent successfully
        """
        if not target.to:
            logger.warning("Email target missing recipients")
            return False

        if not self._settings.smtp_host:
            logger.warning("SMTP not configured")
            return False

        # Build email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._extract_subject(task.message)
        msg["From"] = self._settings.smtp_from or self._settings.smtp_user
        msg["To"] = ", ".join(target.to)

        # Add plain text and HTML parts
        text_part = MIMEText(task.message, "plain", "utf-8")
        html_part = MIMEText(self._to_html(task.message), "html", "utf-8")
        msg.attach(text_part)
        msg.attach(html_part)

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_user or None,
                password=self._settings.smtp_password or None,
                use_tls=not self._settings.smtp_use_tls,
                start_tls=self._settings.smtp_use_tls,
            )
            logger.info("Email sent", recipients=target.to, task_id=task.task_id)
            return True

        except Exception as e:
            logger.error("Email send failed", error=str(e))
            return False

    def _extract_subject(self, message: str) -> str:
        """Extract subject from message (first line)."""
        lines = message.strip().split("\n")
        if lines:
            # Remove markdown formatting
            subject = lines[0].strip("# ").strip("*")
            return subject[:100]  # Limit length
        return "Notification"

    def _to_html(self, message: str) -> str:
        """Convert markdown-like message to basic HTML."""
        html = message.replace("\n", "<br>")
        # Bold
        import re
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        return f"<html><body>{html}</body></html>"
