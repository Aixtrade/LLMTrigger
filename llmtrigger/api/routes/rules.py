"""Rule management API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from llmtrigger.api.deps import PaginationDep, RuleStoreDep
from llmtrigger.models.rule import Rule, RuleMetadata
from llmtrigger.schemas.common import APIResponse, PaginatedResponse
from llmtrigger.schemas.rule import (
    RuleCreate,
    RuleCreateResponse,
    RuleResponse,
    RuleStatusUpdate,
    RuleUpdate,
)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", response_model=APIResponse[RuleCreateResponse])
async def create_rule(
    data: RuleCreate,
    store: RuleStoreDep,
) -> APIResponse[RuleCreateResponse]:
    """Create a new rule."""
    rule_id = f"rule_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

    rule = Rule(
        rule_id=rule_id,
        name=data.name,
        description=data.description,
        enabled=data.enabled,
        priority=data.priority,
        event_types=data.event_types,
        rule_config=data.rule_config,
        notify_policy=data.notify_policy,
        metadata=RuleMetadata(),
    )

    created = await store.create(rule)

    return APIResponse(
        data=RuleCreateResponse(
            rule_id=created.rule_id,
            created_at=created.metadata.created_at,
        )
    )


@router.get("", response_model=PaginatedResponse[RuleResponse])
async def list_rules(
    store: RuleStoreDep,
    pagination: PaginationDep,
    event_type: str | None = Query(default=None, description="Filter by event type"),
    enabled: bool | None = Query(default=None, description="Filter by enabled status"),
    name_contains: str | None = Query(default=None, description="Filter by name substring"),
) -> PaginatedResponse[RuleResponse]:
    """List all rules with optional filtering."""
    # Get all rules
    if event_type:
        rules = await store.list_by_event_type(event_type, include_disabled=True)
    else:
        rules = await store.list_all()

    # Apply filters
    if enabled is not None:
        rules = [r for r in rules if r.enabled == enabled]
    if name_contains:
        needle = name_contains.lower()
        rules = [r for r in rules if needle in r.name.lower()]

    # Calculate pagination
    total = len(rules)
    start = pagination.offset
    end = start + pagination.page_size
    paginated = rules[start:end]

    return PaginatedResponse(
        data=[RuleResponse.model_validate(r.model_dump()) for r in paginated],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{rule_id}", response_model=APIResponse[RuleResponse])
async def get_rule(
    rule_id: str,
    store: RuleStoreDep,
) -> APIResponse[RuleResponse]:
    """Get a single rule by ID."""
    rule = await store.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    return APIResponse(data=RuleResponse.model_validate(rule.model_dump()))


@router.put("/{rule_id}", response_model=APIResponse[RuleResponse])
async def replace_rule(
    rule_id: str,
    data: RuleCreate,
    store: RuleStoreDep,
) -> APIResponse[RuleResponse]:
    """Replace an existing rule."""
    existing = await store.get(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    updated_rule = Rule(
        rule_id=rule_id,
        name=data.name,
        description=data.description,
        enabled=data.enabled,
        priority=data.priority,
        event_types=data.event_types,
        rule_config=data.rule_config,
        notify_policy=data.notify_policy,
        metadata=existing.metadata,
    )
    result = await store.update(rule_id, updated_rule)

    if not result:
        raise HTTPException(status_code=500, detail="Failed to update rule")

    return APIResponse(data=RuleResponse.model_validate(result.model_dump()))


@router.patch("/{rule_id}", response_model=APIResponse[RuleResponse])
async def update_rule(
    rule_id: str,
    data: RuleUpdate,
    store: RuleStoreDep,
) -> APIResponse[RuleResponse]:
    """Partially update an existing rule."""
    existing = await store.get(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    updated_dict = existing.model_dump()
    updated_dict.update(update_data)

    updated_rule = Rule.model_validate(updated_dict)
    result = await store.update(rule_id, updated_rule)

    if not result:
        raise HTTPException(status_code=500, detail="Failed to update rule")

    return APIResponse(data=RuleResponse.model_validate(result.model_dump()))


@router.delete("/{rule_id}", response_model=APIResponse)
async def delete_rule(
    rule_id: str,
    store: RuleStoreDep,
) -> APIResponse:
    """Delete a rule."""
    deleted = await store.delete(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    return APIResponse(message=f"Rule {rule_id} deleted")


@router.patch("/{rule_id}/status", response_model=APIResponse[RuleResponse])
async def update_rule_status(
    rule_id: str,
    data: RuleStatusUpdate,
    store: RuleStoreDep,
) -> APIResponse[RuleResponse]:
    """Enable or disable a rule."""
    updated = await store.set_enabled(rule_id, data.enabled)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    rule = await store.get(rule_id)
    return APIResponse(data=RuleResponse.model_validate(rule.model_dump()))
