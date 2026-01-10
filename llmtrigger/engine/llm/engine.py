"""LLM inference engine for intelligent rule evaluation."""

import hashlib
import json
import time

from openai import AsyncOpenAI
from redis.asyncio import Redis

from llmtrigger.context.summarizer import ContextSummarizer
from llmtrigger.core.config import get_settings
from llmtrigger.core.logging import get_logger
from llmtrigger.engine.llm.parser import LLMDecision, parse_llm_response
from llmtrigger.engine.llm.prompt import build_prompt
from llmtrigger.engine.traditional import EvaluationResult
from llmtrigger.models.event import Event
from llmtrigger.models.rule import Rule
from llmtrigger.storage.auxiliary import LLMCacheStore
from llmtrigger.storage.context_store import ContextStore

logger = get_logger(__name__)


class LLMEngine:
    """LLM inference engine for complex rule evaluation."""

    def __init__(self, redis: Redis | None = None):
        """Initialize LLM engine.

        Args:
            redis: Redis client for caching (optional)
        """
        self._settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=self._settings.openai_api_key or "dummy-key",
            base_url=self._settings.openai_base_url,
            timeout=self._settings.openai_timeout,
        )
        self._redis = redis
        self._cache = LLMCacheStore(redis) if redis else None
        self._context_store = ContextStore(redis) if redis else None
        self._summarizer = ContextSummarizer()

    async def evaluate(self, event: Event, rule: Rule) -> EvaluationResult:
        """Evaluate an event against an LLM rule.

        Args:
            event: Event to evaluate
            rule: Rule with LLM configuration

        Returns:
            Evaluation result
        """
        llm_config = rule.rule_config.llm_config
        if not llm_config:
            return EvaluationResult(
                should_trigger=False,
                reason="Missing LLM configuration",
            )

        start_time = time.time()

        # Get context events
        context_events = []
        if self._context_store:
            context_events = await self._context_store.get_events(event.context_key)

        # Generate context summary
        context_summary = self._summarizer.summarize(context_events)

        # Check cache
        cache_key = self._compute_cache_key(rule.rule_id, context_summary, event)
        if self._cache:
            cached = await self._cache.get(rule.rule_id, cache_key)
            if cached:
                logger.debug("LLM cache hit", rule_id=rule.rule_id)
                return EvaluationResult(
                    should_trigger=cached["should_trigger"],
                    confidence=cached["confidence"],
                    reason=cached["reason"] + " (cached)",
                )

        # Build prompt
        system_prompt, user_prompt = build_prompt(
            rule_description=llm_config.description,
            context_summary=context_summary,
            event_type=event.event_type,
            event_timestamp=event.timestamp.isoformat(),
            event_data=json.dumps(event.data, ensure_ascii=False),
        )

        # Call LLM
        try:
            decision = await self._call_llm(system_prompt, user_prompt)
        except Exception as e:
            logger.error("LLM call failed", rule_id=rule.rule_id, error=str(e))
            return EvaluationResult(
                should_trigger=False,
                reason=f"LLM service error: {e}",
            )

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "LLM evaluation complete",
            rule_id=rule.rule_id,
            should_trigger=decision.should_trigger,
            confidence=decision.confidence,
            elapsed_ms=elapsed_ms,
        )

        # Apply confidence threshold
        threshold = llm_config.confidence_threshold
        if decision.should_trigger and decision.confidence < threshold:
            decision = LLMDecision(
                should_trigger=False,
                confidence=decision.confidence,
                reason=f"Confidence {decision.confidence:.2f} below threshold {threshold}",
            )

        # Cache result
        if self._cache:
            await self._cache.set(
                rule.rule_id,
                cache_key,
                {
                    "should_trigger": decision.should_trigger,
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                },
            )

        return EvaluationResult(
            should_trigger=decision.should_trigger,
            confidence=decision.confidence,
            reason=decision.reason,
        )

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> LLMDecision:
        """Call LLM API and parse response.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            Parsed decision
        """
        response = await self._client.chat.completions.create(
            model=self._settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=500,
        )

        content = response.choices[0].message.content or ""
        return parse_llm_response(content)

    @staticmethod
    def _compute_cache_key(rule_id: str, context_summary: str, event: Event) -> str:
        """Compute cache key for LLM result.

        Args:
            rule_id: Rule ID
            context_summary: Context summary string
            event: Current event

        Returns:
            Cache key hash
        """
        data = f"{rule_id}:{context_summary}:{event.event_type}:{json.dumps(event.data)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
