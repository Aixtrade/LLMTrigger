"""Tests for API error response formats."""

from typing import Any

from fastapi.testclient import TestClient

import llmtrigger.api.app as app_module
from llmtrigger.api.app import create_app
from llmtrigger.api.deps import get_rule_store


class FakeRuleStore:
    """Minimal rule store for error response tests."""

    async def get(self, rule_id: str) -> Any | None:
        return None


def _make_client(monkeypatch) -> TestClient:
    async def _noop() -> None:
        return None

    monkeypatch.setattr(app_module, "init_redis_pool", _noop)
    monkeypatch.setattr(app_module, "close_redis_pool", _noop)

    app = create_app()
    app.dependency_overrides[get_rule_store] = lambda: FakeRuleStore()
    return TestClient(app)


def test_http_exception_response_format(monkeypatch) -> None:
    client = _make_client(monkeypatch)

    response = client.get("/api/v1/rules/missing-rule")

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == 404
    assert payload["message"] == "Rule missing-rule not found"
    assert "data" in payload


def test_validation_error_response_format(monkeypatch) -> None:
    client = _make_client(monkeypatch)

    response = client.post("/api/v1/rules", json={"name": ""})

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == 422
    assert payload["message"] == "Validation error"
    assert isinstance(payload["data"], list)
    assert payload["data"]
