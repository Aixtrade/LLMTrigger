"""Auxiliary storage operations (idempotency, caching, queues)."""

import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from llmtrigger.core.config import get_settings
from llmtrigger.models.notification import NotificationTask
from llmtrigger.storage.redis_client import RedisKeys, get_redis


class IdempotencyStore:
    """Idempotency check storage."""

    TTL_SECONDS = 3600  # 1 hour

    def __init__(self, redis: Redis | None = None):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def is_processed(self, event_id: str) -> bool:
        """Check if event has been processed.

        Args:
            event_id: Event ID to check

        Returns:
            True if already processed
        """
        key = RedisKeys.processed(event_id)
        return await self.redis.exists(key) > 0

    async def mark_processed(self, event_id: str) -> bool:
        """Mark event as processed.

        Args:
            event_id: Event ID to mark

        Returns:
            True if newly marked, False if already existed
        """
        key = RedisKeys.processed(event_id)
        result = await self.redis.setnx(key, "1")
        if result:
            await self.redis.expire(key, self.TTL_SECONDS)
        return bool(result)


class LLMCacheStore:
    """LLM result caching storage."""

    TTL_SECONDS = 60  # 1 minute default

    def __init__(self, redis: Redis | None = None):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def get(self, rule_id: str, context_hash: str) -> dict | None:
        """Get cached LLM result.

        Args:
            rule_id: Rule ID
            context_hash: Hash of context data

        Returns:
            Cached result if found
        """
        key = RedisKeys.llm_cache(rule_id, context_hash)
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(
        self,
        rule_id: str,
        context_hash: str,
        result: dict,
        ttl: int | None = None,
    ) -> None:
        """Cache LLM result.

        Args:
            rule_id: Rule ID
            context_hash: Hash of context data
            result: Result to cache
            ttl: TTL in seconds (optional)
        """
        key = RedisKeys.llm_cache(rule_id, context_hash)
        await self.redis.setex(
            key,
            ttl or self.TTL_SECONDS,
            json.dumps(result),
        )


class NotificationQueue:
    """Notification task queue."""

    def __init__(self, redis: Redis | None = None):
        self._redis = redis
        self._settings = get_settings()

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def enqueue(self, task: NotificationTask) -> None:
        """Add task to notification queue.

        Args:
            task: Notification task to enqueue
        """
        await self.redis.lpush(RedisKeys.NOTIFY_QUEUE, task.model_dump_json())

    async def dequeue(self, timeout: int = 5) -> NotificationTask | None:
        """Get next task from queue.

        Args:
            timeout: Blocking timeout in seconds

        Returns:
            Next task if available
        """
        result = await self.redis.brpop(RedisKeys.NOTIFY_QUEUE, timeout=timeout)
        if result:
            _, data = result
            return NotificationTask.model_validate_json(data)
        return None

    async def requeue_with_delay(self, task: NotificationTask) -> None:
        """Requeue task with retry delay.

        Args:
            task: Task to requeue
        """
        task.retry_count += 1
        delay = task.calculate_retry_delay()
        task.retry_after = datetime.now(timezone.utc)

        # For simplicity, just requeue with incremented retry count
        # A production system might use a delayed queue
        await self.enqueue(task)

    async def move_to_dead_letter(self, task: NotificationTask) -> None:
        """Move task to dead letter queue.

        Args:
            task: Failed task
        """
        await self.redis.lpush(RedisKeys.NOTIFY_DEAD_LETTER, task.model_dump_json())

    async def queue_length(self) -> int:
        """Get current queue length.

        Returns:
            Number of tasks in queue
        """
        return await self.redis.llen(RedisKeys.NOTIFY_QUEUE)


class NotificationDedup:
    """Notification deduplication."""

    def __init__(self, redis: Redis | None = None):
        self._redis = redis
        self._settings = get_settings()

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def should_send(self, rule_id: str, context_key: str, cooldown: int | None = None) -> bool:
        """Check if notification should be sent (not in cooldown).

        Args:
            rule_id: Rule ID
            context_key: Context key
            cooldown: Cooldown period in seconds

        Returns:
            True if notification should be sent
        """
        key = RedisKeys.notify_dedup(rule_id, context_key)
        ttl = cooldown or self._settings.notification_default_cooldown

        # Try to set key (returns True if newly set)
        result = await self.redis.setnx(key, "1")
        if result:
            await self.redis.expire(key, ttl)
            return True
        return False


class RateLimiter:
    """Notification rate limiting."""

    def __init__(self, redis: Redis | None = None):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def check_rate_limit(self, rule_id: str, max_per_minute: int) -> bool:
        """Check if rate limit is exceeded.

        Args:
            rule_id: Rule ID
            max_per_minute: Maximum notifications per minute

        Returns:
            True if within limit
        """
        minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        key = RedisKeys.notify_rate(rule_id, minute)

        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 120)  # Expire after 2 minutes

        return count <= max_per_minute
