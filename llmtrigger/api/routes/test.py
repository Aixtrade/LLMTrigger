"""Rule test API routes."""

from fastapi import APIRouter, HTTPException

from llmtrigger.api.deps import RuleStoreDep
from llmtrigger.schemas.common import APIResponse
from llmtrigger.schemas.test import (
    TestRequest,
    TestResponse,
    TestTriggerResult,
    ValidateRequest,
    ValidateResponse,
)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("/test", response_model=APIResponse[TestResponse])
async def test_rule(
    data: TestRequest,
    store: RuleStoreDep,
) -> APIResponse[TestResponse]:
    """Dry-run test a rule against provided events.

    This endpoint evaluates events against a rule without sending notifications.
    """
    rule = await store.get(data.rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {data.rule_id} not found")

    # TODO: Implement actual rule evaluation
    # For now, return a placeholder response
    triggers = [
        TestTriggerResult(
            event_index=i,
            should_trigger=False,
            confidence=None,
            reason="Test evaluation not yet implemented",
        )
        for i in range(len(data.events))
    ]

    return APIResponse(
        data=TestResponse(
            triggers=triggers,
            llm_calls=0,
            total_latency_ms=0,
        )
    )


@router.post("/validate", response_model=APIResponse[ValidateResponse])
async def validate_rule(
    data: ValidateRequest,
) -> APIResponse[ValidateResponse]:
    """Validate rule configuration syntax.

    Returns validation errors if the configuration is invalid.
    """
    errors: list[str] = []

    # Basic validation
    rule_config = data.rule_config

    if "rule_type" not in rule_config:
        errors.append("Missing required field: rule_type")
    elif rule_config["rule_type"] not in ["traditional", "llm", "hybrid"]:
        errors.append(f"Invalid rule_type: {rule_config.get('rule_type')}")

    rule_type = rule_config.get("rule_type")

    if rule_type in ["traditional", "hybrid"]:
        if "pre_filter" not in rule_config:
            errors.append("Traditional/hybrid rules require pre_filter configuration")

    if rule_type in ["llm", "hybrid"]:
        if "llm_config" not in rule_config:
            errors.append("LLM/hybrid rules require llm_config configuration")
        else:
            llm_config = rule_config.get("llm_config", {})
            if not llm_config.get("description"):
                errors.append("LLM config requires description")

    return APIResponse(
        data=ValidateResponse(
            valid=len(errors) == 0,
            errors=errors,
        )
    )
