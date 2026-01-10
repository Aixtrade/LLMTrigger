"""Common API schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    code: int = Field(default=0, description="Response code, 0 for success")
    message: str = Field(default="success", description="Response message")
    data: T | None = Field(default=None, description="Response data")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    code: int = Field(default=0, description="Response code")
    message: str = Field(default="success", description="Response message")
    data: list[T] = Field(default_factory=list, description="List of items")
    total: int = Field(default=0, ge=0, description="Total count")
    page: int = Field(default=1, ge=1, description="Current page")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")


class ErrorResponse(BaseModel):
    """Error response model."""

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    detail: str | None = Field(default=None, description="Error detail")


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
