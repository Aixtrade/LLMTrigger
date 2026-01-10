"""Telegram notification channel."""

from aiogram import Bot

from llmtrigger.core.config import get_settings
from llmtrigger.core.logging import get_logger
from llmtrigger.models.notification import NotificationTask
from llmtrigger.models.rule import NotifyTarget
from llmtrigger.notification.channels.base import NotificationChannel

logger = get_logger(__name__)


class TelegramChannel(NotificationChannel):
    """Telegram Bot notification channel."""

    def __init__(self):
        """Initialize Telegram bot."""
        settings = get_settings()
        self._bot: Bot | None = None
        if settings.telegram_bot_token:
            self._bot = Bot(token=settings.telegram_bot_token)

    @property
    def channel_type(self) -> str:
        return "telegram"

    async def send(self, target: NotifyTarget, task: NotificationTask) -> bool:
        """Send message via Telegram Bot.

        Args:
            target: Target with user_id or chat_id
            task: Notification task

        Returns:
            True if sent successfully
        """
        if not self._bot:
            logger.warning("Telegram bot not configured")
            return False

        chat_id = target.chat_id or target.user_id
        if not chat_id:
            logger.warning("Telegram target missing chat_id/user_id")
            return False

        try:
            await self._bot.send_message(
                chat_id=chat_id,
                text=task.message,
                parse_mode="Markdown",
            )
            logger.info("Telegram message sent", chat_id=chat_id, task_id=task.task_id)
            return True

        except Exception as e:
            logger.error(
                "Telegram send failed",
                chat_id=chat_id,
                error=str(e),
            )
            return False

    async def close(self) -> None:
        """Close bot session."""
        if self._bot:
            await self._bot.session.close()
