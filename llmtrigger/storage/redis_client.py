"""Redis client management."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as redis
from redis.asyncio import Redis

from llmtrigger.core.config import get_settings

# Global connection pool
_pool: redis.ConnectionPool | None = None


async def init_redis_pool() -> None:
    """Initialize Redis connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )


async def close_redis_pool() -> None:
    """Close Redis connection pool."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


def get_redis() -> Redis:
    """Get Redis client from pool.

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If pool not initialized
    """
    if _pool is None:
        raise RuntimeError("Redis pool not initialized. Call init_redis_pool() first.")
    return redis.Redis(connection_pool=_pool)


@asynccontextmanager
async def redis_client() -> AsyncIterator[Redis]:
    """Context manager for Redis client.

    Usage:
        async with redis_client() as r:
            await r.get("key")
    """
    client = get_redis()
    try:
        yield client
    finally:
        await client.aclose()


# Key prefixes
class RedisKeys:
    """Redis key patterns."""

    # Rules
    RULE_DETAIL = "trigger:rules:detail:{rule_id}"
    RULE_INDEX = "trigger:rules:index:{event_type}"
    RULE_ALL = "trigger:rules:all"
    RULE_VERSION = "trigger:rules:version"
    RULE_UPDATE_CHANNEL = "trigger:rules:update"

    # Context
    CONTEXT = "trigger:context:{context_key}"

    # Auxiliary
    PROCESSED = "trigger:processed:{event_id}"
    LLM_CACHE = "trigger:llm_cache:{rule_id}:{context_hash}"
    NOTIFY_QUEUE = "trigger:notify:queue"
    NOTIFY_DEAD_LETTER = "trigger:notify:dead_letter"
    NOTIFY_DEDUP = "trigger:notify:dedup:{rule_id}:{context_key}"
    NOTIFY_RATE = "trigger:notify:rate:{rule_id}:{minute}"

    @classmethod
    def rule_detail(cls, rule_id: str) -> str:
        return cls.RULE_DETAIL.format(rule_id=rule_id)

    @classmethod
    def rule_index(cls, event_type: str) -> str:
        return cls.RULE_INDEX.format(event_type=event_type)

    @classmethod
    def context(cls, context_key: str) -> str:
        return cls.CONTEXT.format(context_key=context_key)

    @classmethod
    def processed(cls, event_id: str) -> str:
        return cls.PROCESSED.format(event_id=event_id)

    @classmethod
    def llm_cache(cls, rule_id: str, context_hash: str) -> str:
        return cls.LLM_CACHE.format(rule_id=rule_id, context_hash=context_hash)

    @classmethod
    def notify_dedup(cls, rule_id: str, context_key: str) -> str:
        return cls.NOTIFY_DEDUP.format(rule_id=rule_id, context_key=context_key)

    @classmethod
    def notify_rate(cls, rule_id: str, minute: str) -> str:
        return cls.NOTIFY_RATE.format(rule_id=rule_id, minute=minute)
