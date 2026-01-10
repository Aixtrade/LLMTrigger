"""Execution history API routes."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from llmtrigger.api.deps import PaginationDep, RuleStoreDep
from llmtrigger.models.execution import ExecutionRecord, NotificationResultStatus
from llmtrigger.schemas.common import APIResponse, PaginatedResponse

router = APIRouter(prefix="/rules", tags=["rules"])


class ExecutionHistoryResponse(ExecutionRecord):
    """Response model for execution history."""

    pass


@router.get("/{rule_id}/history", response_model=PaginatedResponse[ExecutionHistoryResponse])
async def get_rule_history(
    rule_id: str,
    store: RuleStoreDep,
    pagination: PaginationDep,
    triggered: bool | None = Query(default=None, description="Filter by triggered status"),
    start_time: datetime | None = Query(default=None, description="Filter by start time"),
    end_time: datetime | None = Query(default=None, description="Filter by end time"),
) -> PaginatedResponse[ExecutionHistoryResponse]:
    """Get execution history for a specific rule.

    Returns a paginated list of execution records showing when the rule
    was evaluated and whether it triggered notifications.
    """
    # Verify rule exists
    rule = await store.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    # TODO: Implement actual history retrieval from storage
    # For now, return an empty list as placeholder
    records: list[ExecutionHistoryResponse] = []

    return PaginatedResponse(
        data=records,
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )
