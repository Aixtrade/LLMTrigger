"""Rule domain models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RuleType(str, Enum):
    """Rule type enumeration."""

    TRADITIONAL = "traditional"
    LLM = "llm"
    HYBRID = "hybrid"


class TriggerMode(str, Enum):
    """LLM trigger mode enumeration."""

    REALTIME = "realtime"
    BATCH = "batch"
    INTERVAL = "interval"


class NotifyTargetType(str, Enum):
    """Notification target type."""

    TELEGRAM = "telegram"
    WECOM = "wecom"
    EMAIL = "email"


class PreFilter(BaseModel):
    """Traditional rule pre-filter configuration."""

    type: str = Field(default="expression", description="Filter type")
    expression: str = Field(..., description="Filter expression, e.g., 'profit_rate > 0.05'")


class LLMConfig(BaseModel):
    """LLM rule configuration."""

    description: str = Field(..., description="Natural language rule description")
    trigger_mode: TriggerMode = Field(
        default=TriggerMode.REALTIME,
        description="LLM trigger mode",
    )
    # Batch mode settings
    batch_size: int = Field(default=5, ge=1, description="Batch size for batch mode")
    max_wait_seconds: int = Field(
        default=30,
        ge=1,
        description="Max wait seconds for batch mode",
    )
    # Interval mode settings
    interval_seconds: int = Field(
        default=30,
        ge=1,
        description="Interval seconds for interval mode",
    )
    # Common settings
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for triggering",
    )


class RuleConfig(BaseModel):
    """Rule configuration."""

    rule_type: RuleType = Field(..., description="Rule type")
    pre_filter: PreFilter | None = Field(
        default=None,
        description="Pre-filter for traditional/hybrid rules",
    )
    llm_config: LLMConfig | None = Field(
        default=None,
        description="LLM config for llm/hybrid rules",
    )

    @model_validator(mode="after")
    def validate_config(self) -> "RuleConfig":
        """Ensure configuration matches rule type."""
        if self.rule_type == RuleType.TRADITIONAL and not self.pre_filter:
            raise ValueError("pre_filter is required for traditional rules")
        if self.rule_type == RuleType.LLM and not self.llm_config:
            raise ValueError("llm_config is required for llm rules")
        if self.rule_type == RuleType.HYBRID:
            if not self.pre_filter or not self.llm_config:
                raise ValueError("pre_filter and llm_config are required for hybrid rules")
        return self


class NotifyTarget(BaseModel):
    """Notification target configuration."""

    type: NotifyTargetType = Field(..., description="Target type")
    user_id: str | None = Field(default=None, description="Telegram user ID")
    chat_id: str | None = Field(default=None, description="Telegram chat/group ID")
    webhook_key: str | None = Field(default=None, description="WeCom webhook key")
    to: list[str] | None = Field(default=None, description="Email recipients")


class RateLimit(BaseModel):
    """Rate limit configuration."""

    max_per_minute: int = Field(default=5, ge=1, description="Max notifications per minute")
    cooldown_seconds: int = Field(
        default=60,
        ge=0,
        description="Cooldown between same notifications",
    )


class NotifyPolicy(BaseModel):
    """Notification policy configuration."""

    targets: list[NotifyTarget] = Field(
        default_factory=list,
        description="Notification targets",
    )
    rate_limit: RateLimit = Field(
        default_factory=RateLimit,
        description="Rate limit settings",
    )


class RuleMetadata(BaseModel):
    """Rule metadata."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")
    version: int = Field(default=1)


class Rule(BaseModel):
    """Complete rule model."""

    rule_id: str = Field(..., description="Rule unique identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    priority: int = Field(default=100, ge=0, description="Rule priority (higher = more important)")
    event_types: list[str] = Field(..., description="Matched event types")
    context_keys: list[str] = Field(
        default_factory=list,
        description="Matched context key patterns (supports wildcard *)",
    )
    rule_config: RuleConfig = Field(..., description="Rule configuration")
    notify_policy: NotifyPolicy = Field(
        default_factory=NotifyPolicy,
        description="Notification policy",
    )
    metadata: RuleMetadata = Field(
        default_factory=RuleMetadata,
        description="Rule metadata",
    )

    def matches_event_type(self, event_type: str) -> bool:
        """Check if rule matches the given event type."""
        return event_type in self.event_types

    def matches_context_key(self, context_key: str) -> bool:
        """Check if rule matches the given context key (supports wildcard)."""
        if not self.context_keys:
            return True  # No filter means match all

        for pattern in self.context_keys:
            if self._match_pattern(pattern, context_key):
                return True
        return False

    @staticmethod
    def _match_pattern(pattern: str, value: str) -> bool:
        """Match a pattern with wildcard support."""
        if pattern == "*":
            return True
        if "*" not in pattern:
            return pattern == value

        # Simple wildcard matching
        parts = pattern.split("*")
        if len(parts) == 2:
            prefix, suffix = parts
            return value.startswith(prefix) and value.endswith(suffix)

        # More complex patterns - use fnmatch-like logic
        import fnmatch
        return fnmatch.fnmatch(value, pattern)
