"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "LLMTrigger"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # RabbitMQ
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )
    rabbitmq_queue: str = Field(
        default="trigger_events",
        description="Queue name for receiving events",
    )

    # LLM (OpenAI compatible)
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key",
    )
    openai_base_url: str = Field(
        default="http://localhost:11434/v1",
        description="OpenAI compatible API base URL",
    )
    openai_model: str = Field(
        default="qwen2.5:7b",
        description="Model name to use",
    )
    openai_timeout: int = Field(
        default=30,
        description="API request timeout in seconds",
    )

    # Context window
    context_window_seconds: int = Field(
        default=300,
        ge=60,
        description="Context window duration in seconds",
    )
    context_max_events: int = Field(
        default=100,
        ge=10,
        description="Maximum events per context window",
    )

    # Notification
    notification_max_retry: int = Field(
        default=3,
        ge=1,
        description="Maximum notification retry attempts",
    )
    notification_default_cooldown: int = Field(
        default=60,
        ge=0,
        description="Default notification cooldown in seconds",
    )

    # Telegram (optional)
    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token",
    )

    # Email (optional)
    smtp_host: str = Field(default="", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_from: str = Field(default="", description="Email sender address")
    smtp_use_tls: bool = Field(default=True, description="Use STARTTLS (port 587). Set False for SSL (port 465)")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
