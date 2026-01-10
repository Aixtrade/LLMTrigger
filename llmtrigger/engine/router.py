"""Rule router for intelligent dispatching."""

from redis.asyncio import Redis

from llmtrigger.core.logging import get_logger
from llmtrigger.engine.llm.engine import LLMEngine
from llmtrigger.engine.traditional import EvaluationResult, TraditionalEngine
from llmtrigger.models.event import Event
from llmtrigger.models.rule import Rule, RuleType

logger = get_logger(__name__)


class RuleRouter:
    """Intelligent router for dispatching rules to appropriate engines."""

    def __init__(self, redis: Redis | None = None):
        """Initialize router with engines.

        Args:
            redis: Redis client for LLM caching
        """
        self._traditional_engine = TraditionalEngine()
        self._llm_engine = LLMEngine(redis)

    async def evaluate(self, event: Event, rule: Rule) -> EvaluationResult:
        """Evaluate an event against a rule.

        Routes to appropriate engine based on rule type.

        Args:
            event: Event to evaluate
            rule: Rule to evaluate against

        Returns:
            Evaluation result
        """
        rule_type = rule.rule_config.rule_type

        logger.debug(
            "Routing rule evaluation",
            rule_id=rule.rule_id,
            rule_type=rule_type.value,
        )

        if rule_type == RuleType.TRADITIONAL:
            return self._evaluate_traditional(event, rule)

        elif rule_type == RuleType.LLM:
            return await self._evaluate_llm(event, rule)

        elif rule_type == RuleType.HYBRID:
            return await self._evaluate_hybrid(event, rule)

        else:
            logger.warning("Unknown rule type", rule_type=rule_type)
            return EvaluationResult(
                should_trigger=False,
                reason=f"Unknown rule type: {rule_type}",
            )

    def _evaluate_traditional(self, event: Event, rule: Rule) -> EvaluationResult:
        """Evaluate using traditional engine.

        Args:
            event: Event to evaluate
            rule: Rule with pre_filter

        Returns:
            Evaluation result
        """
        return self._traditional_engine.evaluate(event, rule)

    async def _evaluate_llm(self, event: Event, rule: Rule) -> EvaluationResult:
        """Evaluate using LLM engine.

        Args:
            event: Event to evaluate
            rule: Rule with llm_config

        Returns:
            Evaluation result
        """
        return await self._llm_engine.evaluate(event, rule)

    async def _evaluate_hybrid(self, event: Event, rule: Rule) -> EvaluationResult:
        """Evaluate using hybrid approach (traditional pre-filter + LLM).

        Args:
            event: Event to evaluate
            rule: Rule with both pre_filter and llm_config

        Returns:
            Evaluation result
        """
        # Step 1: Traditional pre-filter
        if rule.rule_config.pre_filter:
            pre_result = self._traditional_engine.evaluate(event, rule)

            if not pre_result.should_trigger:
                logger.debug(
                    "Hybrid rule pre-filter rejected",
                    rule_id=rule.rule_id,
                    reason=pre_result.reason,
                )
                return EvaluationResult(
                    should_trigger=False,
                    reason=f"Pre-filter: {pre_result.reason}",
                )

        # Step 2: LLM deep analysis
        if rule.rule_config.llm_config:
            llm_result = await self._llm_engine.evaluate(event, rule)

            if llm_result.should_trigger:
                return EvaluationResult(
                    should_trigger=True,
                    confidence=llm_result.confidence,
                    reason=f"Pre-filter passed, LLM: {llm_result.reason}",
                )
            else:
                return EvaluationResult(
                    should_trigger=False,
                    confidence=llm_result.confidence,
                    reason=f"LLM: {llm_result.reason}",
                )

        # Fallback: pre-filter only
        return EvaluationResult(
            should_trigger=True,
            confidence=1.0,
            reason="Pre-filter passed (no LLM config)",
        )
