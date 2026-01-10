# Repository Guidelines

## Project Structure & Module Organization
The Python package lives in `llmtrigger/` and is organized by domain: `api/` (FastAPI app and routes), `engine/` (rule and LLM logic), `messaging/` (RabbitMQ consumer), `notification/` (channels + worker), `storage/` (Redis access), and `core/` (config/logging). Tests are under `tests/` with `unit/` and `integration/` subfolders. Architecture notes are in `docs/` (see `docs/architecture.md`), and infrastructure dependencies are defined in `docker-compose.yml`.

## Build, Test, and Development Commands
- `uv sync --dev` installs dependencies using the lockfile (`uv.lock`). If you prefer pip, install from `pyproject.toml`.
- `docker-compose up -d redis rabbitmq` starts required services locally.
- `uvicorn llmtrigger.api.app:app --reload` runs the FastAPI API server with hot reload.
- `python -m llmtrigger.worker` runs the background worker for consuming events and sending notifications.
- `pytest` runs the full test suite (uses `pytest-asyncio`).

## Coding Style & Naming Conventions
Use 4-space indentation and follow PEP 8 with type hints for public functions. Modules and files are `snake_case`, classes are `PascalCase`, and constants are `UPPER_SNAKE_CASE`. Keep config in `llmtrigger/core/config.py`, and prefer explicit imports from the package root.

## Testing Guidelines
Tests use `pytest` with async support. Name files `test_*.py` and keep unit tests in `tests/unit/` while integration tests go in `tests/integration/`. Add tests for new behavior or bug fixes; no coverage threshold is enforced.

## Commit & Pull Request Guidelines
Git history favors clear, sentence-case commit messages (often full sentences describing the change). Keep messages specific and avoid vague tags. For PRs, include a concise description, testing notes (commands + results), and any config or environment variable changes. Link relevant issues and mention new dependencies or services.

## Configuration & Secrets
Settings load from environment variables and `.env` (see `llmtrigger/core/config.py`). Common entries include `REDIS_URL`, `RABBITMQ_URL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`. Do not commit secrets; use `.env` locally.
