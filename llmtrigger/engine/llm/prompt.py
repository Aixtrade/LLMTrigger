"""Prompt templates for LLM inference."""

SYSTEM_PROMPT = """You are a professional event analysis assistant. Your task is to analyze events and determine whether they match user-defined rules.

You will receive:
1. A user-defined rule description
2. Historical context (recent events in a time window)
3. Current event data

Based on this information, you need to:
1. Analyze whether the current event (combined with historical context) satisfies the user's rule
2. Provide a confidence score (0.0 to 1.0)
3. Explain your reasoning

Always respond in JSON format with the following structure:
{
  "should_trigger": true/false,
  "confidence": 0.0-1.0,
  "reason": "Detailed explanation of your decision"
}

Important guidelines:
- Be conservative: only trigger when you are reasonably confident (confidence >= 0.7)
- Consider temporal patterns when the rule involves sequences or trends
- Use specific data from the events to support your reasoning
- If the data is insufficient to make a determination, set should_trigger to false
"""

USER_PROMPT_TEMPLATE = """
## User Rule
{rule_description}

## Historical Context
{context_summary}

## Current Event
Type: {event_type}
Time: {event_timestamp}
Data: {event_data}

Please analyze whether this event satisfies the user's rule. Respond in JSON format.
"""


def build_prompt(
    rule_description: str,
    context_summary: str,
    event_type: str,
    event_timestamp: str,
    event_data: str,
) -> tuple[str, str]:
    """Build system and user prompts for LLM inference.

    Args:
        rule_description: Natural language rule description
        context_summary: Formatted context summary
        event_type: Current event type
        event_timestamp: Current event timestamp
        event_data: Current event data as JSON string

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        rule_description=rule_description,
        context_summary=context_summary or "No historical events in context window.",
        event_type=event_type,
        event_timestamp=event_timestamp,
        event_data=event_data,
    )

    return SYSTEM_PROMPT, user_prompt
