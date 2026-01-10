"""Execution record domain models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NotificationResultStatus(str, Enum):
    """Notification result status."""

    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"  # Skipped due to rate limit or dedup


class ExecutionRecord(BaseModel):
    """Record of rule execution for a specific event."""

    execution_id: str = Field(..., description="Execution unique identifier")
    rule_id: str = Field(..., description="Rule that was evaluated")
    event_id: str = Field(..., description="Event that triggered evaluation")
    context_key: str = Field(..., description="Context key")
    triggered: bool = Field(..., description="Whether rule was triggered")
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="LLM confidence score (if applicable)",
    )
    reason: str = Field(default="", description="Decision reason")
    notification_status: NotificationResultStatus = Field(
        default=NotificationResultStatus.QUEUED,
        description="Notification result status",
    )
    latency_ms: int = Field(default=0, ge=0, description="Processing latency in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
