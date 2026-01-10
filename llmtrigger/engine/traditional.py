"""Traditional rule engine for simple expression-based rules."""

from dataclasses import dataclass

from llmtrigger.core.logging import get_logger
from llmtrigger.engine.expression import evaluate_expression
from llmtrigger.models.event import Event
from llmtrigger.models.rule import Rule

logger = get_logger(__name__)


@dataclass
class EvaluationResult:
    """Result of rule evaluation."""

    should_trigger: bool
    confidence: float | None = None
    reason: str = ""


class TraditionalEngine:
    """Traditional rule engine using expression evaluation."""

    def evaluate(self, event: Event, rule: Rule) -> EvaluationResult:
        """Evaluate a traditional rule against an event.

        Args:
            event: Event to evaluate
            rule: Rule with pre_filter configuration

        Returns:
            Evaluation result
        """
        pre_filter = rule.rule_config.pre_filter
        if not pre_filter:
            logger.warning("Traditional rule missing pre_filter", rule_id=rule.rule_id)
            return EvaluationResult(
                should_trigger=False,
                reason="Missing pre_filter configuration",
            )

        expression = pre_filter.expression

        # Build context from event data
        context = {
            "event_type": event.event_type,
            "context_key": event.context_key,
            **event.data,
        }

        try:
            result = evaluate_expression(expression, context)

            if result:
                return EvaluationResult(
                    should_trigger=True,
                    confidence=1.0,  # Traditional rules have 100% confidence
                    reason=f"Expression '{expression}' evaluated to true",
                )
            else:
                return EvaluationResult(
                    should_trigger=False,
                    reason=f"Expression '{expression}' evaluated to false",
                )

        except ValueError as e:
            logger.error(
                "Expression evaluation failed",
                rule_id=rule.rule_id,
                expression=expression,
                error=str(e),
            )
            return EvaluationResult(
                should_trigger=False,
                reason=f"Expression evaluation error: {e}",
            )


# Singleton instance
_engine: TraditionalEngine | None = None


def get_traditional_engine() -> TraditionalEngine:
    """Get traditional engine singleton."""
    global _engine
    if _engine is None:
        _engine = TraditionalEngine()
    return _engine
