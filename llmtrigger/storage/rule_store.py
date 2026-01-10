"""Rule storage operations."""

import json
from datetime import datetime

from redis.asyncio import Redis

from llmtrigger.models.rule import Rule
from llmtrigger.storage.redis_client import RedisKeys, get_redis


class RuleStore:
    """Rule storage operations using Redis."""

    def __init__(self, redis: Redis | None = None):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def create(self, rule: Rule) -> Rule:
        """Create a new rule.

        Args:
            rule: Rule to create

        Returns:
            Created rule
        """
        key = RedisKeys.rule_detail(rule.rule_id)

        # Store rule details as hash
        await self.redis.hset(
            key,
            mapping={
                "config": rule.model_dump_json(),
                "enabled": str(rule.enabled).lower(),
                "version": str(rule.metadata.version),
                "created_at": str(int(rule.metadata.created_at.timestamp() * 1000)),
                "updated_at": str(int(rule.metadata.updated_at.timestamp() * 1000)),
            },
        )

        # Add to global rule set
        await self.redis.sadd(RedisKeys.RULE_ALL, rule.rule_id)

        # Add to event type indexes
        for event_type in rule.event_types:
            await self.redis.sadd(RedisKeys.rule_index(event_type), rule.rule_id)

        # Increment global version and publish update
        await self._publish_update("create", rule.rule_id)

        return rule

    async def get(self, rule_id: str) -> Rule | None:
        """Get a rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule if found, None otherwise
        """
        key = RedisKeys.rule_detail(rule_id)
        data = await self.redis.hget(key, "config")
        if not data:
            return None
        return Rule.model_validate_json(data)

    async def update(self, rule_id: str, rule: Rule) -> Rule | None:
        """Update an existing rule.

        Args:
            rule_id: Rule ID to update
            rule: Updated rule data

        Returns:
            Updated rule if found, None otherwise
        """
        existing = await self.get(rule_id)
        if not existing:
            return None

        # Update metadata
        rule.metadata.updated_at = datetime.utcnow()
        rule.metadata.version = existing.metadata.version + 1

        key = RedisKeys.rule_detail(rule_id)

        # Update event type indexes if changed
        old_types = set(existing.event_types)
        new_types = set(rule.event_types)

        for removed_type in old_types - new_types:
            await self.redis.srem(RedisKeys.rule_index(removed_type), rule_id)
        for added_type in new_types - old_types:
            await self.redis.sadd(RedisKeys.rule_index(added_type), rule_id)

        # Update rule details
        await self.redis.hset(
            key,
            mapping={
                "config": rule.model_dump_json(),
                "enabled": str(rule.enabled).lower(),
                "version": str(rule.metadata.version),
                "updated_at": str(int(rule.metadata.updated_at.timestamp() * 1000)),
            },
        )

        await self._publish_update("update", rule_id)
        return rule

    async def delete(self, rule_id: str) -> bool:
        """Delete a rule.

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if deleted, False if not found
        """
        existing = await self.get(rule_id)
        if not existing:
            return False

        key = RedisKeys.rule_detail(rule_id)

        # Remove from event type indexes
        for event_type in existing.event_types:
            await self.redis.srem(RedisKeys.rule_index(event_type), rule_id)

        # Remove from global set
        await self.redis.srem(RedisKeys.RULE_ALL, rule_id)

        # Delete rule details
        await self.redis.delete(key)

        await self._publish_update("delete", rule_id)
        return True

    async def list_all(self) -> list[Rule]:
        """List all rules.

        Returns:
            List of all rules
        """
        rule_ids = await self.redis.smembers(RedisKeys.RULE_ALL)
        rules = []
        for rule_id in rule_ids:
            rule = await self.get(rule_id)
            if rule:
                rules.append(rule)
        return rules

    async def list_by_event_type(self, event_type: str) -> list[Rule]:
        """List rules matching an event type.

        Args:
            event_type: Event type to filter by

        Returns:
            List of matching rules (sorted by priority descending)
        """
        rule_ids = await self.redis.smembers(RedisKeys.rule_index(event_type))
        rules = []
        for rule_id in rule_ids:
            rule = await self.get(rule_id)
            if rule and rule.enabled:
                rules.append(rule)

        # Sort by priority (higher first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules

    async def set_enabled(self, rule_id: str, enabled: bool) -> bool:
        """Set rule enabled status.

        Args:
            rule_id: Rule ID
            enabled: New enabled status

        Returns:
            True if updated, False if not found
        """
        rule = await self.get(rule_id)
        if not rule:
            return False

        rule.enabled = enabled
        rule.metadata.updated_at = datetime.utcnow()

        key = RedisKeys.rule_detail(rule_id)
        await self.redis.hset(
            key,
            mapping={
                "config": rule.model_dump_json(),
                "enabled": str(enabled).lower(),
                "updated_at": str(int(rule.metadata.updated_at.timestamp() * 1000)),
            },
        )

        await self._publish_update("update", rule_id)
        return True

    async def get_version(self) -> int:
        """Get global rules version number.

        Returns:
            Current version number
        """
        version = await self.redis.get(RedisKeys.RULE_VERSION)
        return int(version) if version else 0

    async def _publish_update(self, action: str, rule_id: str) -> None:
        """Publish rule update notification.

        Args:
            action: Action type (create/update/delete)
            rule_id: Affected rule ID
        """
        # Increment version
        await self.redis.incr(RedisKeys.RULE_VERSION)

        # Publish update message
        message = json.dumps({
            "action": action,
            "rule_id": rule_id,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
        })
        await self.redis.publish(RedisKeys.RULE_UPDATE_CHANNEL, message)
