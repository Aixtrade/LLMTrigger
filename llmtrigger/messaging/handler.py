"""Event processing handler."""

import time
from typing import Any

from llmtrigger.core.logging import get_logger
from llmtrigger.models.event import Event
from llmtrigger.storage.auxiliary import IdempotencyStore
from llmtrigger.storage.context_store import ContextStore
from llmtrigger.storage.redis_client import get_redis
from llmtrigger.storage.rule_store import RuleStore

logger = get_logger(__name__)


class EventHandler:
    """Main event processing handler."""

    def __init__(self):
        """Initialize handler with storage dependencies."""
        self._redis = get_redis()
        self._idempotency = IdempotencyStore(self._redis)
        self._context_store = ContextStore(self._redis)
        self._rule_store = RuleStore(self._redis)

    async def handle_event(self, event: Event) -> None:
        """Process an incoming event through the full pipeline.

        Pipeline steps:
        1. Idempotency check
        2. Update context window
        3. Load matching rules
        4. Evaluate rules
        5. Queue notifications

        Args:
            event: Event to process
        """
        start_time = time.time()

        logger.info(
            "Processing event",
            event_id=event.event_id,
            event_type=event.event_type,
            context_key=event.context_key,
        )

        # Step 1: Idempotency check
        if not await self._idempotency.mark_processed(event.event_id):
            logger.debug("Event already processed", event_id=event.event_id)
            return

        # Step 2: Update context window
        await self._context_store.add_event(event)

        # Step 3: Load matching rules
        rules = await self._rule_store.list_by_event_type(event.event_type)
        if not rules:
            logger.debug("No rules match event type", event_type=event.event_type)
            return

        logger.info(
            "Found matching rules",
            event_type=event.event_type,
            rule_count=len(rules),
        )

        # Step 4 & 5: Evaluate rules and queue notifications
        for rule in rules:
            try:
                await self._evaluate_rule(event, rule)
            except Exception as e:
                logger.error(
                    "Error evaluating rule",
                    rule_id=rule.rule_id,
                    error=str(e),
                    exc_info=True,
                )

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Event processing complete",
            event_id=event.event_id,
            elapsed_ms=elapsed_ms,
        )

    async def _evaluate_rule(self, event: Event, rule: Any) -> None:
        """Evaluate a single rule against an event.

        Args:
            event: Event being evaluated
            rule: Rule to evaluate
        """
        from llmtrigger.engine.router import RuleRouter

        router = RuleRouter(self._redis)
        result = await router.evaluate(event, rule)

        if result.should_trigger:
            logger.info(
                "Rule triggered",
                rule_id=rule.rule_id,
                event_id=event.event_id,
                confidence=result.confidence,
                reason=result.reason,
            )

            # Queue notification
            await self._queue_notification(event, rule, result)
        else:
            logger.debug(
                "Rule not triggered",
                rule_id=rule.rule_id,
                event_id=event.event_id,
                reason=result.reason,
            )

    async def _queue_notification(self, event: Event, rule: Any, result: Any) -> None:
        """Queue notification for sending.

        Args:
            event: Triggering event
            rule: Triggered rule
            result: Evaluation result
        """
        from llmtrigger.notification.dispatcher import NotificationDispatcher

        dispatcher = NotificationDispatcher(self._redis)
        await dispatcher.dispatch(event, rule, result)


# Singleton handler instance
_handler: EventHandler | None = None


def get_event_handler() -> EventHandler:
    """Get or create event handler singleton."""
    global _handler
    if _handler is None:
        _handler = EventHandler()
    return _handler


async def handle_event(event: Event) -> None:
    """Handle an event using the singleton handler.

    This is the main entry point for event processing.

    Args:
        event: Event to process
    """
    handler = get_event_handler()
    await handler.handle_event(event)
