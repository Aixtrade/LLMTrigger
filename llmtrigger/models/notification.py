"""Notification task domain models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from llmtrigger.models.rule import NotifyTarget


class NotificationStatus(str, Enum):
    """Notification task status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DEAD = "dead"  # Exceeded max retries


class NotificationTask(BaseModel):
    """Notification task for async processing."""

    task_id: str = Field(..., description="Task unique identifier")
    rule_id: str = Field(..., description="Associated rule ID")
    context_key: str = Field(..., description="Context key that triggered notification")
    targets: list[NotifyTarget] = Field(..., description="Notification targets")
    message: str = Field(..., description="Notification message content")
    retry_count: int = Field(default=0, ge=0, description="Current retry count")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    retry_after: datetime | None = Field(
        default=None,
        description="Earliest retry time (for delayed retries)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (decision reason, confidence, etc.)",
    )

    def should_retry(self, max_retry: int) -> bool:
        """Check if task should be retried."""
        return self.retry_count < max_retry

    def calculate_retry_delay(self, base_delay: float = 1.0) -> float:
        """Calculate exponential backoff delay in seconds."""
        return base_delay * (2 ** self.retry_count)
