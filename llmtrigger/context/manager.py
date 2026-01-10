"""Context window manager."""

from redis.asyncio import Redis

from llmtrigger.models.event import Event
from llmtrigger.storage.context_store import ContextStore


class ContextManager:
    """Manager for event context windows.

    Provides high-level operations for context management.
    """

    def __init__(self, redis: Redis | None = None):
        """Initialize context manager.

        Args:
            redis: Redis client (optional, will use default if not provided)
        """
        self._store = ContextStore(redis)

    async def add_event(self, event: Event) -> None:
        """Add an event to its context window.

        Args:
            event: Event to add
        """
        await self._store.add_event(event)

    async def get_context(self, context_key: str, limit: int | None = None) -> list[Event]:
        """Get events from a context window.

        Args:
            context_key: Context key to query
            limit: Maximum events to return

        Returns:
            List of events in chronological order
        """
        return await self._store.get_events(context_key, limit)

    async def get_context_size(self, context_key: str) -> int:
        """Get number of events in a context window.

        Args:
            context_key: Context key to query

        Returns:
            Number of events
        """
        return await self._store.get_event_count(context_key)

    async def clear_context(self, context_key: str) -> None:
        """Clear all events from a context window.

        Args:
            context_key: Context key to clear
        """
        await self._store.clear_context(context_key)
