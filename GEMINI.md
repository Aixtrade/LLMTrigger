# LLMTrigger

## Project Overview

LLMTrigger is a hybrid intelligent event trigger system that combines a traditional rules engine with LLM-based reasoning to monitor events and send notifications. It is designed to be an independent service that ingests events via RabbitMQ, processes them using a hybrid engine (Expression-based + LLM), and dispatches notifications through various channels (Email, Telegram, WeCom).

**Key Technologies:**
- **Language:** Python 3.12+
- **Web Framework:** FastAPI
- **Message Broker:** RabbitMQ (`aio-pika`)
- **State Store:** Redis (`redis-py`)
- **LLM Integration:** OpenAI API
- **Package Manager:** `uv`

## Architecture

The system consists of two main runnable components:
1.  **API Service:** Manages rules, testing, and history.
2.  **Worker Service:** Consumes events from RabbitMQ, executes rules, and handles notifications.

**Core Components (`llmtrigger/`):**
-   `api/`: FastAPI application, routes for rule management (`/rules`), history, and testing.
-   `engine/`: Contains the logic for the hybrid rule engine.
    -   `traditional.py`: Fast, expression-based filtering.
    -   `llm/`: LLM-based reasoning, prompt management, and parsing.
    -   `router.py`: Routes events to the appropriate engine.
-   `messaging/`: RabbitMQ consumer and event handlers.
-   `storage/`: Redis client wrappers for rules (`rule_store.py`) and context (`context_store.py`).
-   `notification/`: Handles dispatching notifications to various channels (`email`, `telegram`, `wecom`) with rate limiting and retries.
-   `core/`: Configuration (`config.py`) and logging.

**Data Flow:**
1.  External system sends event to RabbitMQ.
2.  Worker consumes event.
3.  Event context is updated in Redis.
4.  Rules are matched (Traditional first, then LLM if needed).
5.  If triggered, a notification task is enqueued.
6.  Notification worker sends the message via the configured channel.

## Building and Running

### Prerequisites
-   Python 3.12+
-   Docker (for Redis and RabbitMQ)
-   `uv` (recommended)

### Setup
1.  **Environment Variables:**
    ```bash
    cp .env.example .env
    # Edit .env with your configuration (Redis, RabbitMQ, OpenAI keys)
    ```

2.  **Infrastructure:**
    ```bash
    docker-compose up -d
    ```

3.  **Dependencies:**
    ```bash
    uv sync --dev
    ```

### Execution Commands
*   **Run API:**
    ```bash
    uv run uvicorn llmtrigger.api.app:app --reload --port 8203
    ```
    API documentation available at `http://localhost:8203/docs`.

*   **Run Worker:**
    ```bash
    uv run python -m llmtrigger.worker
    ```

## Testing

The project uses `pytest` for testing.

*   **Run All Tests:**
    ```bash
    uv run pytest
    ```
*   **Test Structure:**
    -   `tests/unit/`: Unit tests for individual components.
    -   `tests/integration/`: Integration tests requiring service interaction.

## Development Conventions

*   **Code Style:** Follow PEP 8. Use 4 spaces for indentation.
*   **Type Hints:** Strictly use type hints for all public functions and classes.
*   **Configuration:** All configuration should be managed via `llmtrigger/core/config.py` and environment variables. Do not hardcode secrets.
*   **Project Structure:**
    -   Keep modules decoupled.
    -   Use `schemas/` for Pydantic models used in API and internal data exchange.
    -   Use `models/` for internal domain models.
*   **Language:** The primary language for documentation and code comments is English. However, `AGENTS.md` notes a preference for Chinese in communication.
