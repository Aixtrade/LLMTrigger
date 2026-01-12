# LLMTrigger Agent Guide

## 1. Purpose
- This file guides agentic coding assistants working in this repo.
- Follow instructions in more specific `AGENTS.md` files if present.
- Keep changes minimal and focused.

## 2. Tech Stack
- Python 3.12+, FastAPI, aio-pika (RabbitMQ), redis.asyncio, OpenAI API.
- Package manager: `uv`.
- Tests: `pytest` + `pytest-asyncio`.
- Lint/format: `ruff`; typing: `mypy`.

## 3. Repo Layout
- `llmtrigger/` main package
- `llmtrigger/api/` FastAPI routes (`/rules`, `/history`, `/test`)
- `llmtrigger/core/` config + logging
- `llmtrigger/engine/` traditional + LLM logic
- `llmtrigger/engine/llm/` prompts + parsing
- `llmtrigger/messaging/` RabbitMQ consumers
- `llmtrigger/notification/` dispatch + channels
- `llmtrigger/storage/` Redis persistence
- `tests/unit/` unit tests
- `tests/integration/` integration tests

## 4. Setup & Services
- Install deps (dev): `uv sync --dev`
- Start infra: `docker-compose up -d redis rabbitmq`
- Stop infra: `docker-compose down`
- Copy env: `cp .env.example .env`
- Fill `REDIS_URL`, `RABBITMQ_URL`, `OPENAI_API_KEY`

## 5. Run Locally
- API (dev): `uv run uvicorn llmtrigger.api.app:app --reload`
- Worker: `uv run python -m llmtrigger.worker`
- Optional: set `LOG_LEVEL=DEBUG` for verbose logs

## 6. Tests
- All tests: `uv run pytest`
- Single file: `uv run pytest tests/unit/test_expression.py`
- Single test: `uv run pytest tests/unit/test_expression.py::test_evaluate_simple_expression`
- Markers: use `@pytest.mark.asyncio` for async tests
- Coverage: `uv run pytest --cov=llmtrigger --cov-report=html`

## 7. Lint & Format
- Lint: `uv run ruff check llmtrigger/`
- Format: `uv run ruff format llmtrigger/`
- Type check: `uv run mypy llmtrigger/`
- Run format before lint when unsure

## 8. Code Style
- Indentation: 4 spaces, no tabs.
- Formatting: follow PEP 8; use `ruff format`.
- Imports: absolute imports preferred; keep sorted (isort compatible).
- Avoid wildcard imports.
- Keep functions small and single-purpose.
- Avoid unnecessary abstraction or cleverness.

### Typing
- Type hints required for public functions, methods, and class attributes.
- Use explicit return types for public functions.
- Prefer `typing` primitives (`list`, `dict`, `tuple`) with generics.
- Use `Optional[T]`/`T | None` consistently.
- Avoid `Any` unless unavoidable; document why.

### Naming
- Files/modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Avoid one-letter names except for tight scopes.
- Use descriptive parameter names for external APIs.

### Async & IO
- Prefer async APIs for IO (`aio-pika`, `redis.asyncio`).
- Do not block the event loop with sync IO or heavy CPU work.
- Use `await` for network/database calls.
- Use `asyncio.create_task` carefully; track lifecycle.
- Tests for async code must use `@pytest.mark.asyncio`.

### Configuration & Secrets
- Never hardcode secrets or URLs.
- Read settings from `llmtrigger.core.config.settings`.
- Add new settings to config module + `.env.example`.
- Keep defaults sensible for local development.

### Error Handling & Logging
- Raise specific exceptions; avoid bare `Exception`.
- API layer: use FastAPI `HTTPException` for client errors.
- Worker/consumer: catch exceptions to avoid crashing loop.
- Log with `structlog` via `llmtrigger.core` logger.
- Include context fields (rule_id, event_id) when logging.

### LLM Integration
- Keep prompts in `llmtrigger/engine/llm/`.
- Avoid leaking secrets into prompts.
- Parse model responses defensively; validate outputs.

### Storage & Messaging
- Redis access should be async and pooled.
- RabbitMQ consumers must ack/nack appropriately.
- Handle transient network failures with retries/backoff.

### Testing Guidance
- Keep tests deterministic; avoid network calls without mocks.
- Use fixtures where possible; prefer focused unit tests.
- Mark integration tests clearly under `tests/integration`.
- Prefer testing behavior over implementation details.

## 9. Feature Notes
### New Rule Types
- Update validation in `models/rule.py`.
- Add routing in `llmtrigger/engine/router.py`.
- Ensure any new config fields are documented.

### New Notification Channels
- Add a new module under `llmtrigger/notification/channels/`.
- Implement `BaseNotificationChannel.send`.
- Register in `NotifyTargetType` and dispatcher.
- Add unit tests for channel behavior when feasible.

## 10. Agent Workflow
- Prefer Chinese (中文) for communication and PR summaries.
- Code comments/docstrings should be English.
- Use absolute paths in tool calls.
- Verify working directory with `pwd` if needed.
- If imports fail, run `uv sync --dev`.
- Do not create extra docs unless requested.
- Avoid touching unrelated files.

## 11. Git & PR Expectations
- Commit messages: sentence-case English or Chinese.
- PRs should include summary and test commands run.
- Mention any config changes or new env vars.
- Do not amend commits unless explicitly requested.

## 12. Env Var Reference
- `REDIS_URL` default `redis://localhost:6379/0`
- `RABBITMQ_URL` default `amqp://guest:guest@localhost:5672/`
- `OPENAI_API_KEY` required for LLM features
- `OPENAI_MODEL` default `gpt-4-turbo-preview`
- `LOG_LEVEL` default `INFO`

## 13. Docs & Comments
- Keep docstrings short and in English.
- Update README or docs only when requested.
- Avoid inline comments unless needed for clarity.

## 14. Cursor/Copilot Rules
- No `.cursor/rules`, `.cursorrules`, or Copilot instructions found.
