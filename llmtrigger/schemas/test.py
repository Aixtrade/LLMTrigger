"""Rule test API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TestEvent(BaseModel):
    """Event data for dry-run testing."""

    event_type: str = Field(..., description="Event type")
    context_key: str = Field(default="", description="Context key")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict, description="Event data")


class TestRequest(BaseModel):
    """Request schema for rule dry-run test."""

    rule_id: str = Field(..., description="Rule ID to test")
    events: list[TestEvent] = Field(..., min_length=1, description="Test events")
    dry_run: bool = Field(default=True, description="Dry run mode (no actual notifications)")


class TestTriggerResult(BaseModel):
    """Result for a single event evaluation."""

    event_index: int = Field(..., description="Index of the event in the request")
    should_trigger: bool = Field(..., description="Whether rule should trigger")
    confidence: float | None = Field(default=None, description="LLM confidence (if applicable)")
    reason: str = Field(default="", description="Decision reason")


class TestResponse(BaseModel):
    """Response schema for rule dry-run test."""

    triggers: list[TestTriggerResult] = Field(
        default_factory=list,
        description="Trigger results for each event",
    )
    llm_calls: int = Field(default=0, description="Number of LLM API calls made")
    total_latency_ms: int = Field(default=0, description="Total processing time in ms")


class ValidateRequest(BaseModel):
    """Request schema for rule validation."""

    rule_config: dict[str, Any] = Field(..., description="Rule configuration to validate")


class ValidateResponse(BaseModel):
    """Response schema for rule validation."""

    valid: bool = Field(..., description="Whether configuration is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
