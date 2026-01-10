# LLMTrigger

[English](README.md) | [中文](README.zh-CN.md)

Hybrid intelligent event trigger system that combines a traditional rules engine with LLM-based reasoning to monitor events and send notifications.

## Overview
- FastAPI API for rule management, testing, and history.
- Hybrid rule engine: expression-based filters + LLM validation.
- RabbitMQ for event ingestion; Redis for state, context, and throttling.
- Notification channels for email, Telegram, and WeCom (extensible).
- Observability hooks for metrics and tracing.

## Quick Start
### Prerequisites
- Python 3.12+
- Docker (for Redis + RabbitMQ)
- `uv` (recommended) or another Python environment manager

### Setup
```bash
cp .env.example .env
docker-compose up -d
uv sync --dev
```

### Run API
```bash
uv run uvicorn llmtrigger.api.app:app --reload
```

### Run Worker
```bash
uv run python -m llmtrigger.worker
```

API docs: `http://localhost:8000/docs`

## Configuration
Settings are loaded from environment variables and `.env`. Common options:
- `REDIS_URL`, `RABBITMQ_URL`, `RABBITMQ_QUEUE`
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- `NOTIFICATION_MAX_RETRY`, `NOTIFICATION_DEFAULT_COOLDOWN`

Keep secrets out of version control and use `.env` locally.

## Project Structure
- `llmtrigger/api/`: FastAPI app, dependencies, and routes
- `llmtrigger/engine/`: rule engine and LLM logic
- `llmtrigger/messaging/`: RabbitMQ consumer and handlers
- `llmtrigger/storage/`: Redis clients and stores
- `llmtrigger/notification/`: notification dispatcher, worker, channels
- `llmtrigger/core/`: config and logging
- `tests/`: unit and integration tests
- `docs/`: architecture and design notes

## Testing
```bash
uv run pytest
```

Tests use `pytest` + `pytest-asyncio` and live under `tests/`.

## Contributing
See `AGENTS.md` for contributor guidelines, style, and PR expectations.

## License
MIT License. See `LICENSE`.
