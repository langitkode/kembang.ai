"""Pagination schemas for reusable pagination responses."""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel


T = TypeVar('T')


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    pagination: PaginationInfo


# Specific pagination response schemas
class ConversationPaginationResponse(BaseModel):
    """Paginated conversations response."""
    conversations: list[dict]
    pagination: PaginationInfo


class ProductPaginationResponse(BaseModel):
    """Paginated products response."""
    products: list[dict]
    pagination: PaginationInfo


class FAQPaginationResponse(BaseModel):
    """Paginated FAQs response."""
    faqs: list[dict]
    pagination: PaginationInfo
