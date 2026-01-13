"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_redis() -> AsyncIterator[None]:
    """Mock Redis for testing without actual Redis connection.

    TODO: Implement proper mock or use fakeredis
    """
    yield None


@pytest.fixture
def sample_event_data() -> dict:
    """Sample event data for testing."""
    return {
        "event_id": "evt_test_001",
        "event_type": "trade.profit",
        "context_key": "trade.profit.BTCUSDT.MACD_Strategy",
        "timestamp": "2026-01-10T14:30:00Z",
        "data": {
            "symbol": "BTCUSDT",
            "strategy": "MACD_Strategy",
            "profit": 1250.50,
            "profit_rate": 0.125,
        },
    }


@pytest.fixture
def sample_rule_data() -> dict:
    """Sample rule data for testing."""
    return {
        "name": "连续盈利告警",
        "description": "当策略连续3次盈利且累计收益超过10%时通知",
        "enabled": True,
        "priority": 100,
        "event_types": ["trade.profit"],
        "rule_config": {
            "rule_type": "hybrid",
            "pre_filter": {
                "type": "expression",
                "expression": "profit_rate > 0.05",
            },
            "llm_config": {
                "description": "连续3次盈利且累计收益超过10%",
                "trigger_mode": "batch",
                "batch_size": 5,
                "max_wait_seconds": 30,
                "confidence_threshold": 0.7,
            },
        },
        "notify_policy": {
            "targets": [{"type": "telegram", "chat_id": "123456"}],
            "rate_limit": {"max_per_minute": 5, "cooldown_seconds": 60},
        },
    }
