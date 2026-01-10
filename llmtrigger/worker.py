"""Worker process entry point for message consumption and notification processing."""

import asyncio
import signal
from typing import Any

from llmtrigger.core.config import get_settings
from llmtrigger.core.logging import get_logger, setup_logging
from llmtrigger.messaging.consumer import RabbitMQConsumer
from llmtrigger.messaging.handler import handle_event
from llmtrigger.notification.worker import NotificationWorker
from llmtrigger.storage.redis_client import (
    close_redis_pool,
    get_redis,
    init_redis_pool,
)

logger = get_logger(__name__)


class WorkerManager:
    """Manager for coordinating worker processes."""

    def __init__(self):
        """Initialize worker manager."""
        self._settings = get_settings()
        self._consumer: RabbitMQConsumer | None = None
        self._notification_worker: NotificationWorker | None = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start all worker processes."""
        setup_logging()
        logger.info("Starting worker manager")

        # Initialize Redis
        await init_redis_pool()

        # Create workers
        self._consumer = RabbitMQConsumer(handle_event)
        self._notification_worker = NotificationWorker(get_redis())

        # Start workers concurrently
        try:
            await asyncio.gather(
                self._run_consumer(),
                self._run_notification_worker(),
            )
        finally:
            await self._cleanup()

    async def _run_consumer(self) -> None:
        """Run message consumer."""
        if self._consumer:
            try:
                await self._consumer.start_consuming()
            except asyncio.CancelledError:
                logger.info("Consumer cancelled")
            except Exception as e:
                logger.error("Consumer error", error=str(e), exc_info=True)

    async def _run_notification_worker(self) -> None:
        """Run notification worker."""
        if self._notification_worker:
            try:
                await self._notification_worker.start()
            except asyncio.CancelledError:
                logger.info("Notification worker cancelled")
            except Exception as e:
                logger.error("Notification worker error", error=str(e), exc_info=True)

    async def stop(self) -> None:
        """Signal workers to stop."""
        logger.info("Stopping workers")
        if self._consumer:
            self._consumer.stop()
        if self._notification_worker:
            self._notification_worker.stop()
        self._shutdown_event.set()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up resources")
        if self._consumer:
            await self._consumer.disconnect()
        if self._notification_worker:
            await self._notification_worker.close()
        await close_redis_pool()
        logger.info("Cleanup complete")


async def main() -> None:
    """Main entry point for worker process."""
    manager = WorkerManager()

    # Setup signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start workers
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
