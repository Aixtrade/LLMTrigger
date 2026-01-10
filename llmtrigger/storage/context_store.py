"""Context window storage operations."""

import json
from datetime import datetime
from typing import Any

from redis.asyncio import Redis

from llmtrigger.core.config import get_settings
from llmtrigger.models.event import Event
from llmtrigger.storage.redis_client import RedisKeys, get_redis


class ContextStore:
    """Context window storage using Redis Sorted Sets."""

    def __init__(self, redis: Redis | None = None):
        self._redis = redis
        self._settings = get_settings()

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def add_event(self, event: Event) -> None:
        """Add event to context window.

        Args:
            event: Event to add
        """
        key = RedisKeys.context(event.context_key)
        timestamp_ms = int(event.timestamp.timestamp() * 1000)

        # Add to sorted set with timestamp as score
        entry = json.dumps(event.to_context_entry())
        await self.redis.zadd(key, {entry: timestamp_ms})

        # Cleanup old events
        await self._cleanup(key)

        # Set key expiration
        ttl = self._settings.context_window_seconds + 60
        await self.redis.expire(key, ttl)

    async def get_events(
        self,
        context_key: str,
        limit: int | None = None,
    ) -> list[Event]:
        """Get events from context window.

        Args:
            context_key: Context key to query
            limit: Maximum number of events to return (most recent first)

        Returns:
            List of events in chronological order
        """
        key = RedisKeys.context(context_key)

        # Calculate time cutoff
        cutoff_ms = self._get_cutoff_timestamp()

        # Get events within time window
        entries = await self.redis.zrangebyscore(
            key,
            min=cutoff_ms,
            max="+inf",
            withscores=False,
        )

        events = []
        for entry in entries:
            try:
                data = json.loads(entry)
                event = Event.from_context_entry(data, context_key)
                events.append(event)
            except (json.JSONDecodeError, KeyError):
                continue

        # Apply limit if specified (most recent events)
        if limit and len(events) > limit:
            events = events[-limit:]

        return events

    async def get_event_count(self, context_key: str) -> int:
        """Get number of events in context window.

        Args:
            context_key: Context key to query

        Returns:
            Number of events
        """
        key = RedisKeys.context(context_key)
        cutoff_ms = self._get_cutoff_timestamp()

        return await self.redis.zcount(key, min=cutoff_ms, max="+inf")

    async def clear_context(self, context_key: str) -> None:
        """Clear all events from a context window.

        Args:
            context_key: Context key to clear
        """
        key = RedisKeys.context(context_key)
        await self.redis.delete(key)

    async def _cleanup(self, key: str) -> None:
        """Clean up old events from context window.

        Args:
            key: Redis key for context
        """
        cutoff_ms = self._get_cutoff_timestamp()

        # Remove events outside time window
        await self.redis.zremrangebyscore(key, "-inf", cutoff_ms - 1)

        # Limit by count (keep most recent events)
        max_events = self._settings.context_max_events
        count = await self.redis.zcard(key)
        if count > max_events:
            # Remove oldest events
            await self.redis.zremrangebyrank(key, 0, count - max_events - 1)

    def _get_cutoff_timestamp(self) -> int:
        """Get cutoff timestamp for time window.

        Returns:
            Cutoff timestamp in milliseconds
        """
        now = datetime.utcnow()
        cutoff = now.timestamp() - self._settings.context_window_seconds
        return int(cutoff * 1000)
