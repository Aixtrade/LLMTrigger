"""RabbitMQ message consumer."""

import asyncio
import json
from typing import Any, Callable, Coroutine

import aio_pika
from aio_pika import IncomingMessage
from aio_pika.abc import AbstractRobustConnection

from llmtrigger.core.config import get_settings
from llmtrigger.core.logging import get_logger
from llmtrigger.models.event import Event

logger = get_logger(__name__)

# Type alias for message handler
MessageHandler = Callable[[Event], Coroutine[Any, Any, None]]


class RabbitMQConsumer:
    """RabbitMQ message consumer for event processing."""

    def __init__(self, handler: MessageHandler):
        """Initialize consumer.

        Args:
            handler: Async function to handle incoming events
        """
        self._settings = get_settings()
        self._handler = handler
        self._connection: AbstractRobustConnection | None = None
        self._should_stop = False

    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        self._connection = await aio_pika.connect_robust(
            self._settings.rabbitmq_url,
            reconnect_interval=5,
        )
        logger.info("Connected to RabbitMQ")

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Disconnected from RabbitMQ")

    async def start_consuming(self) -> None:
        """Start consuming messages from queue."""
        if not self._connection:
            await self.connect()

        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=10)

        queue = await channel.declare_queue(
            self._settings.rabbitmq_queue,
            durable=True,
        )

        logger.info("Starting message consumption", queue=self._settings.rabbitmq_queue)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                if self._should_stop:
                    break
                await self._process_message(message)

    async def _process_message(self, message: IncomingMessage) -> None:
        """Process a single message.

        Args:
            message: Incoming RabbitMQ message
        """
        async with message.process():
            try:
                # Parse message body
                body = json.loads(message.body.decode())

                # Validate required fields
                if "event_type" not in body:
                    logger.warning("Message missing event_type", message_id=message.message_id)
                    return

                # Create event model
                event = Event(
                    event_id=body.get("event_id", message.message_id or ""),
                    event_type=body["event_type"],
                    context_key=body.get("context_key", ""),
                    timestamp=body.get("timestamp"),
                    data=body.get("data", {}),
                )

                logger.debug(
                    "Processing event",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    context_key=event.context_key,
                )

                # Handle event
                await self._handler(event)

            except json.JSONDecodeError as e:
                logger.error("Invalid JSON message", error=str(e))
            except Exception as e:
                logger.error("Error processing message", error=str(e), exc_info=True)

    def stop(self) -> None:
        """Signal consumer to stop."""
        self._should_stop = True
        logger.info("Consumer stop requested")


async def create_consumer(handler: MessageHandler) -> RabbitMQConsumer:
    """Create and connect a RabbitMQ consumer.

    Args:
        handler: Event handler function

    Returns:
        Connected consumer instance
    """
    consumer = RabbitMQConsumer(handler)
    await consumer.connect()
    return consumer
