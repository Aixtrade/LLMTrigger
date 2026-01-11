"""Trigger mode management for LLM rules.

This module implements different trigger strategies for LLM analysis:
- REALTIME: Every event triggers LLM analysis
- BATCH: Accumulate events until batch_size or max_wait_seconds
- INTERVAL: Analyze at fixed intervals regardless of events
"""

import json
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from redis.asyncio import Redis

from llmtrigger.core.logging import get_logger
from llmtrigger.models.event import Event
from llmtrigger.models.rule import LLMConfig, Rule, TriggerMode
from llmtrigger.storage.redis_client import RedisKeys, get_redis

logger = get_logger(__name__)


class TriggerDecision(str, Enum):
    """Decision on whether to trigger LLM analysis."""

    TRIGGER = "trigger"  # Should execute LLM analysis now
    SKIP = "skip"  # Skip this event, conditions not met
    PENDING = "pending"  # Event added to batch, waiting for more


@dataclass
class TriggerResult:
    """Result of trigger mode check."""

    decision: TriggerDecision
    reason: str
    batch_events: list[Event] | None = None  # For batch mode, accumulated events


class TriggerModeStore:
    """Storage for trigger mode state."""

    TTL_SECONDS = 3600  # 1 hour default TTL

    def __init__(self, redis: Redis | None = None):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def add_to_batch(
        self,
        rule_id: str,
        context_key: str,
        event: Event,
        max_wait_seconds: int,
    ) -> int:
        """Add event to batch queue.

        Args:
            rule_id: Rule ID
            context_key: Context key
            event: Event to add
            max_wait_seconds: TTL for batch

        Returns:
            Current batch size
        """
        key = RedisKeys.trigger_batch(rule_id, context_key)
        entry = json.dumps(event.to_context_entry())

        # Add to list
        await self.redis.rpush(key, entry)

        # Set TTL on first event
        ttl = await self.redis.ttl(key)
        if ttl == -1:  # No TTL set
            await self.redis.expire(key, max_wait_seconds + 10)

        return await self.redis.llen(key)

    async def get_batch(self, rule_id: str, context_key: str) -> list[Event]:
        """Get all events in batch.

        Args:
            rule_id: Rule ID
            context_key: Context key

        Returns:
            List of accumulated events
        """
        key = RedisKeys.trigger_batch(rule_id, context_key)
        entries = await self.redis.lrange(key, 0, -1)

        events = []
        for entry in entries:
            try:
                data = json.loads(entry)
                event = Event.from_context_entry(data, context_key)
                events.append(event)
            except (json.JSONDecodeError, KeyError):
                continue

        return events

    async def clear_batch(self, rule_id: str, context_key: str) -> None:
        """Clear batch after processing.

        Args:
            rule_id: Rule ID
            context_key: Context key
        """
        key = RedisKeys.trigger_batch(rule_id, context_key)
        await self.redis.delete(key)

    async def get_batch_first_timestamp(self, rule_id: str, context_key: str) -> float | None:
        """Get timestamp of first event in batch.

        Args:
            rule_id: Rule ID
            context_key: Context key

        Returns:
            Timestamp in seconds, or None if batch is empty
        """
        key = RedisKeys.trigger_batch(rule_id, context_key)
        first = await self.redis.lindex(key, 0)

        if first:
            try:
                data = json.loads(first)
                raw_ts = data.get("timestamp")
                if isinstance(raw_ts, (int, float)):
                    return float(raw_ts)
                if isinstance(raw_ts, str):
                    dt = datetime.fromisoformat(raw_ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.timestamp()
            except (json.JSONDecodeError, KeyError):
                pass

        return None

    async def set_last_analysis_time(
        self,
        rule_id: str,
        context_key: str,
        timestamp: float | None = None,
    ) -> None:
        """Record last LLM analysis time.

        Args:
            rule_id: Rule ID
            context_key: Context key
            timestamp: Analysis timestamp (defaults to now)
        """
        key = RedisKeys.trigger_last_analysis(rule_id, context_key)
        ts = timestamp or time.time()
        await self.redis.setex(key, self.TTL_SECONDS, str(ts))

    async def get_last_analysis_time(self, rule_id: str, context_key: str) -> float | None:
        """Get last LLM analysis time.

        Args:
            rule_id: Rule ID
            context_key: Context key

        Returns:
            Timestamp in seconds, or None if never analyzed
        """
        key = RedisKeys.trigger_last_analysis(rule_id, context_key)
        value = await self.redis.get(key)

        if value:
            try:
                return float(value)
            except ValueError:
                pass

        return None

    async def try_acquire_interval_lock(self, rule_id: str, interval_seconds: int) -> bool:
        """Try to acquire interval lock for periodic analysis.

        Args:
            rule_id: Rule ID
            interval_seconds: Lock duration

        Returns:
            True if lock acquired, False if already locked
        """
        key = RedisKeys.trigger_interval_lock(rule_id)
        result = await self.redis.setnx(key, str(time.time()))
        if result:
            await self.redis.expire(key, interval_seconds)
        return bool(result)


class TriggerModeManager:
    """Manager for different LLM trigger modes."""

    def __init__(self, redis: Redis | None = None):
        self._redis = redis
        self._store = TriggerModeStore(redis)

    async def should_trigger(
        self,
        event: Event,
        rule: Rule,
    ) -> TriggerResult:
        """Determine if LLM analysis should be triggered.

        Args:
            event: Current event
            rule: Rule being evaluated

        Returns:
            TriggerResult with decision and reason
        """
        llm_config = rule.rule_config.llm_config
        if not llm_config:
            return TriggerResult(
                decision=TriggerDecision.SKIP,
                reason="No LLM config",
            )

        mode = llm_config.trigger_mode

        if mode == TriggerMode.REALTIME:
            return await self._check_realtime(event, rule, llm_config)
        elif mode == TriggerMode.BATCH:
            return await self._check_batch(event, rule, llm_config)
        elif mode == TriggerMode.INTERVAL:
            return await self._check_interval(event, rule, llm_config)
        else:
            logger.warning("Unknown trigger mode", mode=mode)
            return TriggerResult(
                decision=TriggerDecision.TRIGGER,
                reason=f"Unknown mode {mode}, falling back to realtime",
            )

    async def mark_analyzed(self, rule: Rule, context_key: str) -> None:
        """Mark that LLM analysis was performed.

        Call this after successful LLM analysis to update state.

        Args:
            rule: Rule that was analyzed
            context_key: Context key that was analyzed
        """
        llm_config = rule.rule_config.llm_config
        if not llm_config:
            return

        # Record analysis time
        await self._store.set_last_analysis_time(rule.rule_id, context_key)

        # Clear batch if applicable
        if llm_config.trigger_mode == TriggerMode.BATCH:
            await self._store.clear_batch(rule.rule_id, context_key)

    async def _check_realtime(
        self,
        event: Event,
        rule: Rule,
        llm_config: LLMConfig,
    ) -> TriggerResult:
        """Check realtime mode - always trigger.

        Every event triggers LLM analysis immediately.
        """
        return TriggerResult(
            decision=TriggerDecision.TRIGGER,
            reason="Realtime mode: analyze every event",
        )

    async def _check_batch(
        self,
        event: Event,
        rule: Rule,
        llm_config: LLMConfig,
    ) -> TriggerResult:
        """Check batch mode - accumulate until threshold.

        Triggers when:
        1. Batch size reaches batch_size, OR
        2. Time since first event exceeds max_wait_seconds
        """
        batch_size = llm_config.batch_size
        max_wait = llm_config.max_wait_seconds

        # Add to batch
        current_size = await self._store.add_to_batch(
            rule.rule_id,
            event.context_key,
            event,
            max_wait,
        )

        # Check size threshold
        if current_size >= batch_size:
            batch_events = await self._store.get_batch(rule.rule_id, event.context_key)
            return TriggerResult(
                decision=TriggerDecision.TRIGGER,
                reason=f"Batch full: {current_size}/{batch_size} events",
                batch_events=batch_events,
            )

        # Check time threshold
        first_ts = await self._store.get_batch_first_timestamp(
            rule.rule_id,
            event.context_key,
        )
        if first_ts:
            elapsed = time.time() - first_ts
            if elapsed >= max_wait:
                batch_events = await self._store.get_batch(rule.rule_id, event.context_key)
                return TriggerResult(
                    decision=TriggerDecision.TRIGGER,
                    reason=f"Batch timeout: {elapsed:.1f}s >= {max_wait}s",
                    batch_events=batch_events,
                )

        return TriggerResult(
            decision=TriggerDecision.PENDING,
            reason=f"Batch pending: {current_size}/{batch_size} events",
        )

    async def _check_interval(
        self,
        event: Event,
        rule: Rule,
        llm_config: LLMConfig,
    ) -> TriggerResult:
        """Check interval mode - analyze at fixed intervals.

        Triggers when interval_seconds has passed since last analysis.
        Uses a lock to ensure only one analysis per interval.
        """
        interval = llm_config.interval_seconds

        # Check last analysis time
        last_time = await self._store.get_last_analysis_time(
            rule.rule_id,
            event.context_key,
        )

        if last_time:
            elapsed = time.time() - last_time
            if elapsed < interval:
                return TriggerResult(
                    decision=TriggerDecision.SKIP,
                    reason=f"Interval not reached: {elapsed:.1f}s < {interval}s",
                )

        # Try to acquire lock to prevent concurrent triggers
        if await self._store.try_acquire_interval_lock(rule.rule_id, interval):
            return TriggerResult(
                decision=TriggerDecision.TRIGGER,
                reason=f"Interval reached: analyzing at {interval}s interval",
            )

        return TriggerResult(
            decision=TriggerDecision.SKIP,
            reason="Interval analysis already in progress",
        )
