"""Context window storage operations."""

import json
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

        # Set key expiration (rely on Redis TTL instead of manual cleanup)
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

        # Get all events (rely on Redis TTL for expiration)
        entries = await self.redis.zrange(key, 0, -1)

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

        # Count all events (rely on Redis TTL for expiration)
        return await self.redis.zcard(key)

    async def clear_context(self, context_key: str) -> None:
        """Clear all events from a context window.

        Args:
            context_key: Context key to clear
        """
        key = RedisKeys.context(context_key)
        await self.redis.delete(key)
