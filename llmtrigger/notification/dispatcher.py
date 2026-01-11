"""Notification dispatcher for queuing notifications."""

import uuid
from typing import Any

from redis.asyncio import Redis

from llmtrigger.core.logging import get_logger
from llmtrigger.engine.traditional import EvaluationResult
from llmtrigger.models.event import Event
from llmtrigger.models.notification import NotificationTask
from llmtrigger.models.rule import Rule
from llmtrigger.notification.rate_limiter import NotificationRateLimiter
from llmtrigger.storage.auxiliary import NotificationQueue

logger = get_logger(__name__)


class NotificationDispatcher:
    """Dispatcher for queuing notifications."""

    def __init__(self, redis: Redis):
        """Initialize dispatcher.

        Args:
            redis: Redis client
        """
        self._redis = redis
        self._queue = NotificationQueue(redis)
        self._rate_limiter = NotificationRateLimiter(redis)

    async def dispatch(
        self,
        event: Event,
        rule: Rule,
        result: EvaluationResult,
    ) -> bool:
        """Dispatch notification for a triggered rule.

        Args:
            event: Triggering event
            rule: Triggered rule
            result: Evaluation result

        Returns:
            True if notification was queued
        """
        notify_policy = rule.notify_policy
        if not notify_policy.targets:
            logger.debug("No notification targets", rule_id=rule.rule_id)
            return False

        # Check rate limits
        rate_limit = notify_policy.rate_limit
        allowed, reason = await self._rate_limiter.check_allowed(
            rule_id=rule.rule_id,
            context_key=event.context_key,
            max_per_minute=rate_limit.max_per_minute,
            cooldown=rate_limit.cooldown_seconds,
        )

        if not allowed:
            logger.info(
                "Notification skipped",
                rule_id=rule.rule_id,
                reason=reason,
            )
            return False

        # Build notification message
        message = self._build_message(event, rule, result)

        # Create notification task
        task = NotificationTask(
            task_id=f"notify_{uuid.uuid4().hex[:12]}",
            rule_id=rule.rule_id,
            context_key=event.context_key,
            targets=notify_policy.targets,
            message=message,
            metadata={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "confidence": result.confidence,
                "reason": result.reason,
            },
        )

        # Queue for async processing
        await self._queue.enqueue(task)

        logger.info(
            "Notification queued",
            task_id=task.task_id,
            rule_id=rule.rule_id,
            targets=len(notify_policy.targets),
        )

        return True

    def _build_message(
        self,
        event: Event,
        rule: Rule,
        result: EvaluationResult,
    ) -> str:
        """Build notification message.

        Args:
            event: Triggering event
            rule: Triggered rule
            result: Evaluation result

        Returns:
            Formatted message (HTML format for Telegram)
        """
        import html

        # Escape HTML special characters
        def escape(text: Any) -> str:
            return html.escape(str(text))

        lines = [
            f"🔔 <b>{escape(rule.name)}</b>",
            "",
            f"⏰ <b>触发时间:</b> {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"📌 <b>事件类型:</b> {escape(event.event_type)}",
            "",
            f"💡 <b>触发原因:</b>",
            f"{escape(result.reason)}",
        ]

        if result.confidence:
            lines.append(f"📊 <b>置信度:</b> {result.confidence:.0%}")

        # Add event data summary
        if event.data:
            lines.append("")
            lines.append("📦 <b>事件数据:</b>")
            for key, value in list(event.data.items())[:5]:  # Limit fields
                lines.append(f"  • {escape(key)}: {escape(value)}")

        return "\n".join(lines)
