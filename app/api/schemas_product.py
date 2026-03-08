"""Product schemas for request/response validation."""

import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ── Request Schemas ──────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    """Schema for creating a product."""
    
    sku: str = Field(..., min_length=1, max_length=50, description="Stock Keeping Unit")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: str = Field(..., min_length=1, max_length=100, description="Product category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Product subcategory")
    
    price: Decimal = Field(..., gt=0, description="Product price in IDR")
    discount_price: Optional[Decimal] = Field(None, gt=0, description="Discounted price")
    
    stock_quantity: int = Field(default=0, ge=0, description="Available stock")
    is_active: bool = Field(default=True, description="Whether product is available")
    
    attributes: Optional[dict] = Field(None, description="Product attributes (skin_type, benefits, etc.)")
    images: Optional[list[str]] = Field(None, description="List of image URLs")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    
    price: Optional[Decimal] = Field(None, gt=0)
    discount_price: Optional[Decimal] = Field(None, gt=0)
    
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = Field(None)
    
    attributes: Optional[dict] = Field(None)
    images: Optional[list[str]] = Field(None)


# ── Response Schemas ─────────────────────────────────────────────────────────


class ProductOut(BaseModel):
    """Schema for product response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    tenant_id: str
    sku: str
    name: str
    description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    
    price: float
    discount_price: Optional[float] = None
    final_price: float  # Computed field
    
    stock_quantity: int
    is_active: bool
    is_in_stock: bool  # Computed field
    
    attributes: Optional[dict] = None
    images: Optional[list[str]] = None
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProductListResponse(BaseModel):
    """Schema for product list response."""
    
    products: list[ProductOut]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int


class ProductDetailResponse(BaseModel):
    """Schema for single product detail response."""
    
    product: ProductOut


class CatalogMetadataResponse(BaseModel):
    """Schema for catalog metadata response."""
    
    categories: list[str]
    subcategories: list[str]
    skin_types: list[str]
    concerns: list[str]
    price_range: tuple[float, float]


# ── Bulk Upload Schemas ──────────────────────────────────────────────────────


class BulkUploadResponse(BaseModel):
    """Schema for bulk upload response."""
    
    success: bool
    imported_count: int
    failed_count: int
    errors: list[dict] = []
