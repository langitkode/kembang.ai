"""Catalog service - get dynamic categories, skin types, etc. from product catalog."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

logger = logging.getLogger(__name__)


class CatalogService:
    """Service for getting dynamic catalog metadata."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_categories(self, tenant_id: UUID) -> list[str]:
        """Get all unique categories from product catalog."""
        result = await self._db.execute(
            select(distinct(Product.category))
            .where(Product.tenant_id == tenant_id, Product.is_active == True)
            .order_by(Product.category)
        )
        categories = [row[0] for row in result.all() if row[0]]
        logger.info("Found %d categories for tenant %s", len(categories), tenant_id)
        return categories

    async def get_subcategories(
        self,
        tenant_id: UUID,
        category: Optional[str] = None,
    ) -> list[str]:
        """Get all unique subcategories."""
        query = select(distinct(Product.subcategory)).where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
            Product.subcategory.isnot(None),
        )
        
        if category:
            query = query.where(Product.category.ilike(f"%{category}%"))
        
        result = await self._db.execute(query)
        subcategories = [row[0] for row in result.all() if row[0]]
        logger.info("Found %d subcategories for tenant %s", len(subcategories), tenant_id)
        return subcategories

    async def get_skin_types(
        self,
        tenant_id: UUID,
        category: Optional[str] = None,
    ) -> list[str]:
        """Get all unique skin types from product attributes."""
        # Query products with skin_type in attributes
        query = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
            Product.attributes.op("?")("skin_type"),
        )
        
        if category:
            query = query.where(Product.category.ilike(f"%{category}%"))
        
        result = await self._db.execute(query)
        products = result.scalars().all()
        
        # Extract unique skin types from attributes
        skin_types = set()
        for product in products:
            if product.attributes and "skin_type" in product.attributes:
                for st in product.attributes["skin_type"]:
                    skin_types.add(st)
        
        logger.info("Found %d skin types for tenant %s", len(skin_types), tenant_id)
        return sorted(list(skin_types))

    async def get_concerns(
        self,
        tenant_id: UUID,
        category: Optional[str] = None,
    ) -> list[str]:
        """Get all unique concerns/benefits from product attributes."""
        query = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
            Product.attributes.op("?")("benefits"),
        )
        
        if category:
            query = query.where(Product.category.ilike(f"%{category}%"))
        
        result = await self._db.execute(query)
        products = result.scalars().all()
        
        # Extract unique concerns from attributes
        concerns = set()
        for product in products:
            if product.attributes and "benefits" in product.attributes:
                for benefit in product.attributes["benefits"]:
                    concerns.add(benefit)
        
        logger.info("Found %d concerns for tenant %s", len(concerns), tenant_id)
        return sorted(list(concerns))

    async def get_price_range(
        self,
        tenant_id: UUID,
        category: Optional[str] = None,
    ) -> tuple[float, float]:
        """Get min and max price from product catalog."""
        from sqlalchemy import func
        
        # Use price column directly instead of final_price property
        query = select(
            func.min(Product.price),
            func.max(Product.price)
        ).where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
        )
        
        if category:
            query = query.where(Product.category.ilike(f"%{category}%"))
        
        result = await self._db.execute(query)
        row = result.one()
        
        min_price = float(row[0]) if row[0] else 0.0
        max_price = float(row[1]) if row[1] else 0.0
        
        logger.info("Price range for tenant %s: %.0f - %.0f", tenant_id, min_price, max_price)
        return (min_price, max_price)

    async def get_catalog_metadata(self, tenant_id: UUID) -> dict:
        """Get full catalog metadata for conversation flow."""
        categories = await self.get_categories(tenant_id)
        
        metadata = {
            "categories": categories,
            "subcategories": await self.get_subcategories(tenant_id),
            "skin_types": await self.get_skin_types(tenant_id),
            "concerns": await self.get_concerns(tenant_id),
            "price_range": await self.get_price_range(tenant_id),
        }
        
        logger.info("Catalog metadata for tenant %s: %s", tenant_id, metadata)
        return metadata


# ── Helper Functions ──────────────────────────────────────────────────────────

async def get_catalog_service(db: AsyncSession) -> CatalogService:
    """Get catalog service instance."""
    return CatalogService(db)
