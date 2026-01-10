"""Event domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Event model received from message queue."""

    event_id: str = Field(..., description="Event unique identifier for idempotency")
    event_type: str = Field(..., description="Event type, e.g., 'trade.profit'")
    context_key: str = Field(
        default="",
        description="Context grouping key, e.g., 'trade.profit.BTCUSDT.MACD_Strategy'",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload data",
    )

    def model_post_init(self, __context: Any) -> None:
        """Set default context_key if not provided."""
        if not self.context_key:
            self.context_key = self.event_type

    def to_context_entry(self) -> dict[str, Any]:
        """Convert event to context window entry format."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }

    @classmethod
    def from_context_entry(cls, entry: dict[str, Any], context_key: str) -> "Event":
        """Create event from context window entry."""
        return cls(
            event_id=entry["event_id"],
            event_type=entry["event_type"],
            context_key=context_key,
            timestamp=datetime.fromisoformat(entry["timestamp"]),
            data=entry.get("data", {}),
        )
