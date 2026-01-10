"""Notification rate limiting."""

from redis.asyncio import Redis

from llmtrigger.storage.auxiliary import NotificationDedup, RateLimiter


class NotificationRateLimiter:
    """Rate limiter for notifications."""

    def __init__(self, redis: Redis):
        """Initialize rate limiter.

        Args:
            redis: Redis client
        """
        self._dedup = NotificationDedup(redis)
        self._rate_limiter = RateLimiter(redis)

    async def check_allowed(
        self,
        rule_id: str,
        context_key: str,
        max_per_minute: int = 5,
        cooldown: int = 60,
    ) -> tuple[bool, str]:
        """Check if notification is allowed.

        Args:
            rule_id: Rule ID
            context_key: Context key
            max_per_minute: Maximum notifications per minute
            cooldown: Cooldown between same notifications

        Returns:
            Tuple of (allowed, reason)
        """
        # Check deduplication (cooldown)
        if not await self._dedup.should_send(rule_id, context_key, cooldown):
            return False, f"In cooldown period ({cooldown}s)"

        # Check rate limit
        if not await self._rate_limiter.check_rate_limit(rule_id, max_per_minute):
            return False, f"Rate limit exceeded ({max_per_minute}/min)"

        return True, "Allowed"
