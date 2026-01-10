"""Expression evaluation for traditional rules."""

from typing import Any

from simpleeval import simple_eval, EvalWithCompoundTypes

from llmtrigger.core.logging import get_logger

logger = get_logger(__name__)


class ExpressionEvaluator:
    """Safe expression evaluator for rule conditions."""

    # Allowed functions in expressions
    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "round": round,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
    }

    def __init__(self):
        """Initialize evaluator with safe functions."""
        self._evaluator = EvalWithCompoundTypes(functions=self.ALLOWED_FUNCTIONS)

    def evaluate(self, expression: str, context: dict[str, Any]) -> bool:
        """Evaluate an expression with context variables.

        Args:
            expression: Expression string (e.g., "profit_rate > 0.1")
            context: Variable context for evaluation

        Returns:
            Boolean result of expression

        Raises:
            ValueError: If expression is invalid
        """
        try:
            # Flatten nested data for easier access
            flat_context = self._flatten_dict(context)

            result = simple_eval(
                expression,
                names=flat_context,
                functions=self.ALLOWED_FUNCTIONS,
            )

            # Convert to boolean
            return bool(result)

        except Exception as e:
            logger.error(
                "Expression evaluation error",
                expression=expression,
                error=str(e),
            )
            raise ValueError(f"Invalid expression: {expression}") from e

    def validate(self, expression: str) -> tuple[bool, str | None]:
        """Validate expression syntax.

        Args:
            expression: Expression to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to compile the expression with dummy values
            simple_eval(
                expression,
                names={"_dummy": 0},
                functions=self.ALLOWED_FUNCTIONS,
            )
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = "_") -> dict[str, Any]:
        """Flatten nested dictionary.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys

        Returns:
            Flattened dictionary
        """
        items: list[tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(ExpressionEvaluator._flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))
                # Also add with original key for direct access
                items.append((k, v))
        return dict(items)


# Singleton instance
_evaluator: ExpressionEvaluator | None = None


def get_expression_evaluator() -> ExpressionEvaluator:
    """Get expression evaluator singleton."""
    global _evaluator
    if _evaluator is None:
        _evaluator = ExpressionEvaluator()
    return _evaluator


def evaluate_expression(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate expression with context.

    Convenience function using singleton evaluator.

    Args:
        expression: Expression string
        context: Variable context

    Returns:
        Boolean result
    """
    return get_expression_evaluator().evaluate(expression, context)
