"""Product CRUD routes."""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.schemas_product import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductListResponse,
    ProductDetailResponse,
    CatalogMetadataResponse,
    BulkUploadResponse,
)
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.models.product import Product
from app.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


# ── Helper Functions ─────────────────────────────────────────────────────────


def product_to_schema(product: Product) -> ProductOut:
    """Convert Product ORM to Pydantic schema."""
    return ProductOut(
        id=str(product.id),
        tenant_id=str(product.tenant_id),
        sku=product.sku,
        name=product.name,
        description=product.description,
        category=product.category,
        subcategory=product.subcategory,
        price=float(product.price),
        discount_price=float(product.discount_price) if product.discount_price else None,
        final_price=float(product.final_price),
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
        is_in_stock=product.is_in_stock,
        attributes=product.attributes,
        images=product.images,
        created_at=product.created_at.isoformat() if product.created_at else None,
        updated_at=product.updated_at.isoformat() if product.updated_at else None,
    )


# ── CRUD Routes ──────────────────────────────────────────────────────────────


@router.get("", response_model=ProductListResponse)
async def list_products(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Maximum price"),
    in_stock_only: bool = Query(False, description="Show only in-stock products"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List all products for the current tenant with filters."""
    # Build query
    query = select(Product).where(
        Product.tenant_id == tenant.id,
    )
    
    # Apply filters
    if category:
        query = query.where(Product.category.ilike(f"%{category}%"))
    
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    
    if in_stock_only:
        query = query.where(
            Product.stock_quantity > 0,
            Product.is_active == True
        )
    
    if search:
        query = query.where(
            (Product.name.ilike(f"%{search}%")) |
            (Product.description.ilike(f"%{search}%"))
        )
    
    # Get total count
    count_query = select(func.count(Product.id)).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Product.name).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return ProductListResponse(
        products=[product_to_schema(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Get a specific product by ID."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product_not_found",
        )
    
    return ProductDetailResponse(product=product_to_schema(product))


@router.post("", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Create a new product."""
    # Check if SKU already exists for this tenant
    existing = await db.execute(
        select(Product).where(
            Product.sku == body.sku,
            Product.tenant_id == tenant.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="sku_already_exists",
        )
    
    # Create product
    product = Product(
        tenant_id=tenant.id,
        **body.model_dump(),
    )
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    logger.info("Created product %s for tenant %s", product.id, tenant.id)
    
    return ProductDetailResponse(product=product_to_schema(product))


@router.put("/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Update an existing product."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product_not_found",
        )
    
    # Check SKU uniqueness if changing SKU
    if body.sku and body.sku != product.sku:
        existing = await db.execute(
            select(Product).where(
                Product.sku == body.sku,
                Product.tenant_id == tenant.id,
                Product.id != product_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="sku_already_exists",
            )
    
    # Update fields
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    await db.commit()
    await db.refresh(product)
    
    logger.info("Updated product %s for tenant %s", product.id, tenant.id)
    
    return ProductDetailResponse(product=product_to_schema(product))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Delete a product (soft delete by setting is_active=False)."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product_not_found",
        )
    
    # Soft delete
    product.is_active = False
    await db.commit()
    
    logger.info("Deleted product %s for tenant %s", product.id, tenant.id)
    
    return None


# ── Catalog Metadata Routes ─────────────────────────────────────────────────


@router.get("/catalog/metadata", response_model=CatalogMetadataResponse)
async def get_catalog_metadata(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Get catalog metadata for AI slot extraction."""
    catalog_service = CatalogService(db)
    metadata = await catalog_service.get_catalog_metadata(tenant.id)
    
    return CatalogMetadataResponse(
        categories=metadata.get("categories", []),
        subcategories=metadata.get("subcategories", []),
        skin_types=metadata.get("skin_types", []),
        concerns=metadata.get("concerns", []),
        price_range=metadata.get("price_range", (0, 0)),
    )


# ── Bulk Upload Routes ──────────────────────────────────────────────────────


@router.post("/bulk", response_model=BulkUploadResponse)
async def bulk_upload_products(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
    # In production, add file upload handling here
):
    """Bulk upload products from CSV/Excel.
    
    Note: This is a placeholder. In production, add:
    - File upload with UploadFile
    - CSV/Excel parsing
    - Batch insert with error handling
    """
    return BulkUploadResponse(
        success=False,
        imported_count=0,
        failed_count=0,
        errors=[{"message": "Not implemented yet - use individual product creation"}],
    )
