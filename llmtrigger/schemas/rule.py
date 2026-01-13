"""Rule API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from llmtrigger.models.rule import (
    NotifyPolicy,
    RuleConfig,
    RuleMetadata,
)


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""

    name: str = Field(..., min_length=1, max_length=100, description="Rule name")
    description: str = Field(default="", max_length=500, description="Rule description")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    priority: int = Field(default=100, ge=0, le=1000, description="Rule priority")
    event_types: list[str] = Field(..., min_length=1, description="Matched event types")
    rule_config: RuleConfig = Field(..., description="Rule configuration")
    notify_policy: NotifyPolicy = Field(
        default_factory=NotifyPolicy,
        description="Notification policy",
    )


class RuleUpdate(BaseModel):
    """Schema for updating an existing rule."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    event_types: list[str] | None = Field(default=None, min_length=1)
    rule_config: RuleConfig | None = None
    notify_policy: NotifyPolicy | None = None


class RuleStatusUpdate(BaseModel):
    """Schema for updating rule enabled status."""

    enabled: bool = Field(..., description="Whether rule is enabled")


class RuleResponse(BaseModel):
    """Schema for rule response."""

    rule_id: str
    name: str
    description: str
    enabled: bool
    priority: int
    event_types: list[str]
    rule_config: RuleConfig
    notify_policy: NotifyPolicy
    metadata: RuleMetadata


class RuleCreateResponse(BaseModel):
    """Schema for rule creation response."""

    rule_id: str = Field(..., description="Created rule ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class RuleListFilter(BaseModel):
    """Schema for rule list filtering."""

    event_type: str | None = Field(default=None, description="Filter by event type")
    enabled: bool | None = Field(default=None, description="Filter by enabled status")
    name_contains: str | None = Field(default=None, description="Filter by name substring")
