# LLMTrigger Developer Guidelines

## 1. Project Overview & Architecture

LLMTrigger is a hybrid intelligent event trigger system combining a traditional rules engine with LLM-based reasoning. It ingests events via RabbitMQ, processes them using a hybrid engine (Expression + LLM), and dispatches notifications via various channels (Email, Telegram, WeCom).

### Key Technologies
- **Runtime**: Python 3.12+
- **Web Framework**: FastAPI
- **Message Broker**: RabbitMQ (`aio-pika`)
- **State Store**: Redis (`redis-py`)
- **LLM**: OpenAI API integration
- **Package Manager**: `uv`

### Directory Structure
- `llmtrigger/`: Main package
  - `api/`: FastAPI application and routes (`/rules`, `/history`, `/test`)
  - `core/`: Configuration (`config.py`) and logging setup
  - `engine/`: Rule evaluation logic
    - `traditional.py`: Expression-based filtering (`simpleeval`)
    - `llm/`: LLM reasoning engine, prompts, and parsing
    - `router.py`: Routes events to engines based on rule type
  - `messaging/`: RabbitMQ consumer and event handlers
  - `notification/`: Notification dispatching and channel implementations
  - `storage/`: Redis persistence layers (`rule_store`, `context_store`)
- `tests/`: Test suite
  - `unit/`: Component-level tests
  - `integration/`: End-to-end flow tests

## 2. Development Workflow & Commands

### Setup & Dependencies
Manage dependencies using `uv`.
```bash
# Install dependencies (including dev)
uv sync --dev

# Start infrastructure (Redis & RabbitMQ)
docker-compose up -d redis rabbitmq

# Configure environment
cp .env.example .env
# Edit .env to set REDIS_URL, RABBITMQ_URL, and OPENAI_API_KEY
```

### Running Services
The system comprises an API service and a Worker service.

```bash
# Start FastAPI API (Dev mode with hot reload)
uv run uvicorn llmtrigger.api.app:app --reload

# Start Background Worker (Consumes events & sends notifications)
uv run python -m llmtrigger.worker
```

### Testing
Tests are built with `pytest` and `pytest-asyncio`.

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/unit/test_expression.py

# Run a specific test function
uv run pytest tests/unit/test_expression.py::test_evaluate_simple_expression

# Run with coverage report
uv run pytest --cov=llmtrigger --cov-report=html
```

### Linting & Formatting
Enforce code quality standards using `ruff` and `mypy`.

```bash
# Check code style and common errors
uv run ruff check llmtrigger/

# Auto-format code
uv run ruff format llmtrigger/

# Type checking (Optional but recommended)
uv run mypy llmtrigger/
```

## 3. Code Style & Conventions

### General Guidelines
- **Indentation**: Use **4 spaces**. No tabs.
- **Formatting**: Adhere to PEP 8 standards. Use `ruff format` to ensure compliance.
- **Imports**: Prefer explicit absolute imports (e.g., `from llmtrigger.core.config import settings`). Sort imports using standard tools (isort compatible).
- **Paths**: Always use **absolute paths** when performing file operations in your agent tools.

### Typing & Naming
- **Type Hints**: **Mandatory** for all public functions, methods, and class attributes.
- **Modules/Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### Async/Await
- This project is heavily asynchronous (`async`/`await`).
- Use `aio-pika` for RabbitMQ and `redis.asyncio` for Redis.
- Ensure all I/O bound operations are non-blocking.
- Tests must be marked with `@pytest.mark.asyncio`.

### Configuration
- Do **not** hardcode values. Use `llmtrigger.core.config.settings`.
- Secrets (API keys, passwords) must come from environment variables.

## 4. Feature Implementation Guidelines

### Adding a New Rule Type
The system supports `TRADITIONAL`, `LLM`, and `HYBRID` rule types.
- Ensure `models/rule.py` validation logic supports any new configuration fields.
- Update `engine/router.py` to handle routing for the new type.

### Adding a Notification Channel
1. Create a new file in `llmtrigger/notification/channels/` (e.g., `slack.py`).
2. Create a class inheriting from `BaseNotificationChannel`.
3. Implement the `send` method.
4. Add the new type to the `NotifyTargetType` enum.
5. Register the channel in `llmtrigger/notification/dispatcher.py`.

### Error Handling
- Use specific exceptions where possible.
- Log errors using `structlog` (configured in `core`).
- For the API, use FastAPI's `HTTPException` for client errors.
- Ensure the Worker process catches exceptions to prevent crashing the consumer loop.

## 5. Agent Interaction Guidelines

- **Communication Language**: **Chinese (中文)** is preferred for communication (chat, PR descriptions). Code comments and documentation strings should be in **English**.
- **Tool Usage**: 
  - Always verify your current directory (`pwd`) or use absolute paths.
  - Run `uv sync --dev` if you encounter import errors to ensure the environment is up-to-date.
  - If a test fails, analyze the output carefully before attempting a fix.
  - When creating files, ensure the directory structure exists.

## 6. Git & Commit Protocol

- **Commit Messages**: Use clear, sentence-case English or Chinese.
  - Good: "Fix retry logic in notification worker"
  - Good: "修复通知重试逻辑中的死循环问题"
- **Pull Requests**:
  - Include a summary of changes.
  - List commands used to verify the changes (e.g., specific test runs).
  - Mention any configuration changes required.

## 7. Configuration Reference (Key Variables)

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis Connection String | `redis://localhost:6379/0` |
| `RABBITMQ_URL` | RabbitMQ Connection String | `amqp://guest:guest@localhost:5672/` |
| `OPENAI_API_KEY` | OpenAI API Key | Required for LLM features |
| `OPENAI_MODEL` | Model ID | `gpt-4-turbo-preview` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---
*This file is intended to guide AI agents and developers in maintaining the LLMTrigger codebase.*
