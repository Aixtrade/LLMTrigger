"""Notification worker for processing notification queue."""

import asyncio

from redis.asyncio import Redis

from llmtrigger.core.config import get_settings
from llmtrigger.core.logging import get_logger
from llmtrigger.models.notification import NotificationTask
from llmtrigger.models.rule import NotifyTargetType
from llmtrigger.notification.channels.base import NotificationChannel
from llmtrigger.notification.channels.email import EmailChannel
from llmtrigger.notification.channels.telegram import TelegramChannel
from llmtrigger.notification.channels.wecom import WeComChannel
from llmtrigger.storage.auxiliary import NotificationQueue

logger = get_logger(__name__)


class NotificationWorker:
    """Worker for processing notification tasks from queue."""

    def __init__(self, redis: Redis):
        """Initialize worker.

        Args:
            redis: Redis client
        """
        self._redis = redis
        self._settings = get_settings()
        self._queue = NotificationQueue(redis)
        self._should_stop = False

        # Initialize channels
        self._channels: dict[str, NotificationChannel] = {
            NotifyTargetType.TELEGRAM.value: TelegramChannel(),
            NotifyTargetType.WECOM.value: WeComChannel(),
            NotifyTargetType.EMAIL.value: EmailChannel(),
        }

    async def start(self) -> None:
        """Start processing notification queue."""
        logger.info("Notification worker started")

        while not self._should_stop:
            try:
                task = await self._queue.dequeue(timeout=5)
                if task:
                    await self._process_task(task)
            except Exception as e:
                logger.error("Worker error", error=str(e), exc_info=True)
                await asyncio.sleep(1)

        logger.info("Notification worker stopped")

    def stop(self) -> None:
        """Signal worker to stop."""
        self._should_stop = True

    async def close(self) -> None:
        """Clean up resources."""
        for channel in self._channels.values():
            await channel.close()

    async def _process_task(self, task: NotificationTask) -> None:
        """Process a single notification task.

        Args:
            task: Task to process
        """
        logger.debug("Processing notification", task_id=task.task_id)

        success_count = 0
        fail_count = 0

        for target in task.targets:
            channel = self._channels.get(target.type.value)
            if not channel:
                logger.warning("Unknown channel type", channel=target.type)
                continue

            try:
                success = await channel.send(target, task)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(
                    "Channel send error",
                    channel=target.type,
                    error=str(e),
                )
                fail_count += 1

        # Handle failures
        if fail_count > 0 and success_count == 0:
            # All failed - retry
            if task.should_retry(self._settings.notification_max_retry):
                await self._queue.requeue_with_delay(task)
                logger.info(
                    "Notification requeued for retry",
                    task_id=task.task_id,
                    retry_count=task.retry_count + 1,
                )
            else:
                # Max retries exceeded - move to dead letter
                await self._queue.move_to_dead_letter(task)
                logger.warning(
                    "Notification moved to dead letter",
                    task_id=task.task_id,
                )
        else:
            logger.info(
                "Notification processed",
                task_id=task.task_id,
                success=success_count,
                failed=fail_count,
            )
