"""API dependency injection."""

from typing import Annotated

from fastapi import Depends, Query

from llmtrigger.schemas.common import PaginationParams
from llmtrigger.storage.redis_client import get_redis
from llmtrigger.storage.rule_store import RuleStore


def get_rule_store() -> RuleStore:
    """Get rule store instance."""
    return RuleStore(get_redis())


# Type aliases for dependency injection
RuleStoreDep = Annotated[RuleStore, Depends(get_rule_store)]


def get_pagination(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """Get pagination parameters from query."""
    return PaginationParams(page=page, page_size=page_size)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]
