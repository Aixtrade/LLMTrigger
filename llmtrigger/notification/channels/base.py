"""Base class for notification channels."""

from abc import ABC, abstractmethod

from llmtrigger.models.notification import NotificationTask
from llmtrigger.models.rule import NotifyTarget


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Return channel type identifier."""
        pass

    @abstractmethod
    async def send(self, target: NotifyTarget, task: NotificationTask) -> bool:
        """Send notification to target.

        Args:
            target: Notification target configuration
            task: Notification task with message

        Returns:
            True if sent successfully
        """
        pass

    async def close(self) -> None:
        """Clean up resources. Override if needed."""
        pass
