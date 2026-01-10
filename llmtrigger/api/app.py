"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from llmtrigger.api.routes import history, rules, test
from llmtrigger.core.config import get_settings
from llmtrigger.core.logging import get_logger, setup_logging
from llmtrigger.storage.redis_client import close_redis_pool, init_redis_pool

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    settings = get_settings()

    # Startup
    setup_logging()
    logger.info("Starting application", app_name=settings.app_name, version=settings.app_version)

    await init_redis_pool()
    logger.info("Redis connection pool initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_redis_pool()
    logger.info("Redis connection pool closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Hybrid Intelligent Event Trigger System",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(rules.router, prefix="/api/v1")
    app.include_router(test.router, prefix="/api/v1")
    app.include_router(history.router, prefix="/api/v1")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal server error",
                "detail": str(exc) if settings.debug else None,
            },
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "ok", "version": settings.app_version}

    return app


# Application instance for uvicorn
app = create_app()
