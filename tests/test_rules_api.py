"""Tests for rule management behaviors."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from llmtrigger.api.routes import rules as rules_api
from llmtrigger.models.rule import (
    LLMConfig,
    NotifyPolicy,
    PreFilter,
    Rule,
    RuleConfig,
    RuleMetadata,
    RuleType,
)
from llmtrigger.schemas.common import PaginationParams
from llmtrigger.schemas.rule import RuleCreate, RuleUpdate


class FakeRuleStore:
    """In-memory rule store for API tests."""

    def __init__(self, rules: list[Rule]):
        self._rules = {rule.rule_id: rule for rule in rules}
        self.include_disabled: bool | None = None

    async def list_all(self) -> list[Rule]:
        return list(self._rules.values())

    async def list_by_event_type(self, event_type: str, include_disabled: bool = False) -> list[Rule]:
        self.include_disabled = include_disabled
        return [
            rule for rule in self._rules.values()
            if event_type in rule.event_types
        ]

    async def get(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    async def update(self, rule_id: str, rule: Rule) -> Rule | None:
        self._rules[rule_id] = rule
        return rule


def make_rule(
    rule_id: str,
    name: str,
    enabled: bool,
    priority: int,
    event_types: list[str],
    created_at: datetime,
) -> Rule:
    return Rule(
        rule_id=rule_id,
        name=name,
        description="",
        enabled=enabled,
        priority=priority,
        event_types=event_types,
        context_keys=[],
        rule_config=RuleConfig(
            rule_type=RuleType.TRADITIONAL,
            pre_filter=PreFilter(expression="profit_rate > 0.01"),
        ),
        notify_policy=NotifyPolicy(),
        metadata=RuleMetadata(created_at=created_at, updated_at=created_at),
    )


def test_rule_config_requires_llm_config_for_llm_rules() -> None:
    with pytest.raises(ValidationError):
        RuleConfig(rule_type=RuleType.LLM)


def test_rule_config_requires_pre_filter_for_traditional_rules() -> None:
    with pytest.raises(ValidationError):
        RuleConfig(rule_type=RuleType.TRADITIONAL)


def test_rule_config_requires_both_for_hybrid_rules() -> None:
    with pytest.raises(ValidationError):
        RuleConfig(
            rule_type=RuleType.HYBRID,
            pre_filter=PreFilter(expression="profit_rate > 0.01"),
        )
    with pytest.raises(ValidationError):
        RuleConfig(
            rule_type=RuleType.HYBRID,
            llm_config=LLMConfig(description="Detect anomalies"),
        )


def test_rule_update_event_types_requires_non_empty() -> None:
    with pytest.raises(ValidationError):
        RuleUpdate(event_types=[])


@pytest.mark.asyncio
async def test_list_rules_filters_event_type_enabled_and_name() -> None:
    rules = [
        make_rule(
            rule_id="rule_a",
            name="Alpha Rule",
            enabled=True,
            priority=100,
            event_types=["trade.profit"],
            created_at=datetime(2024, 1, 1),
        ),
        make_rule(
            rule_id="rule_b",
            name="Beta Rule",
            enabled=False,
            priority=50,
            event_types=["trade.profit"],
            created_at=datetime(2024, 1, 2),
        ),
        make_rule(
            rule_id="rule_c",
            name="Beta Other",
            enabled=False,
            priority=10,
            event_types=["trade.loss"],
            created_at=datetime(2024, 1, 3),
        ),
    ]
    store = FakeRuleStore(rules)
    pagination = PaginationParams(page=1, page_size=20)

    response = await rules_api.list_rules(
        store=store,
        pagination=pagination,
        event_type="trade.profit",
        enabled=False,
        name_contains="beta",
    )

    assert store.include_disabled is True
    assert response.total == 1
    assert response.data[0].rule_id == "rule_b"


@pytest.mark.asyncio
async def test_patch_rule_updates_selected_fields_only() -> None:
    created_at = datetime(2024, 1, 1)
    rule = make_rule(
        rule_id="rule_patch",
        name="Patch Rule",
        enabled=True,
        priority=100,
        event_types=["trade.profit"],
        created_at=created_at,
    )
    store = FakeRuleStore([rule])

    response = await rules_api.update_rule(
        rule_id="rule_patch",
        data=RuleUpdate(description="Updated description", enabled=False),
        store=store,
    )

    assert response.data is not None
    assert response.data.description == "Updated description"
    assert response.data.enabled is False
    assert response.data.name == "Patch Rule"
    assert response.data.event_types == ["trade.profit"]


@pytest.mark.asyncio
async def test_replace_rule_overwrites_fields() -> None:
    created_at = datetime(2024, 1, 1)
    rule = make_rule(
        rule_id="rule_replace",
        name="Replace Rule",
        enabled=True,
        priority=100,
        event_types=["trade.profit"],
        created_at=created_at,
    )
    store = FakeRuleStore([rule])
    replacement = RuleCreate(
        name="Replacement",
        description="Replaced body",
        enabled=False,
        priority=300,
        event_types=["trade.loss"],
        context_keys=["trade.loss.*"],
        rule_config=RuleConfig(
            rule_type=RuleType.TRADITIONAL,
            pre_filter=PreFilter(expression="profit_rate < -0.05"),
        ),
        notify_policy=NotifyPolicy(),
    )

    response = await rules_api.replace_rule(
        rule_id="rule_replace",
        data=replacement,
        store=store,
    )

    assert response.data is not None
    assert response.data.name == "Replacement"
    assert response.data.description == "Replaced body"
    assert response.data.enabled is False
    assert response.data.priority == 300
    assert response.data.event_types == ["trade.loss"]
