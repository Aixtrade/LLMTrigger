"""Parser for LLM response."""

import json
import re
from dataclasses import dataclass

from llmtrigger.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMDecision:
    """Parsed LLM decision."""

    should_trigger: bool
    confidence: float
    reason: str


def parse_llm_response(response: str) -> LLMDecision:
    """Parse LLM response into structured decision.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed decision

    Note:
        Falls back to safe defaults if parsing fails
    """
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if not json_match:
            logger.warning("No JSON found in LLM response", response=response[:200])
            return _fallback_decision("No JSON found in response")

        json_str = json_match.group()
        data = json.loads(json_str)

        # Extract fields with defaults
        should_trigger = data.get("should_trigger", False)
        confidence = float(data.get("confidence", 0.0))
        reason = data.get("reason", "No reason provided")

        # Validate confidence range
        confidence = max(0.0, min(1.0, confidence))

        # Ensure boolean type
        if isinstance(should_trigger, str):
            should_trigger = should_trigger.lower() == "true"

        return LLMDecision(
            should_trigger=bool(should_trigger),
            confidence=confidence,
            reason=reason,
        )

    except json.JSONDecodeError as e:
        logger.warning("JSON parse error in LLM response", error=str(e))
        return _fallback_decision(f"JSON parse error: {e}")

    except Exception as e:
        logger.error("Error parsing LLM response", error=str(e), exc_info=True)
        return _fallback_decision(f"Parse error: {e}")


def _fallback_decision(reason: str) -> LLMDecision:
    """Create fallback decision when parsing fails.

    Args:
        reason: Error reason

    Returns:
        Safe fallback decision (no trigger)
    """
    return LLMDecision(
        should_trigger=False,
        confidence=0.0,
        reason=f"Fallback decision: {reason}",
    )
