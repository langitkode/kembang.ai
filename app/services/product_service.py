"""Product service - search and retrieve products for sales flow."""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.services.conversation_state_machine import ConversationSlots

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product search and recommendations."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def search_products(
        self,
        tenant_id: UUID,
        slots: ConversationSlots,
        limit: int = 5,
    ) -> list[Product]:
        """Search products based on conversation slots.
        
        Args:
            tenant_id: Tenant identifier
            slots: Conversation slots with product requirements
            limit: Maximum number of products to return
        
        Returns:
            List of matching products
        """
        # Build query
        query = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
            Product.stock_quantity > 0,
        )
        
        # Filter by category/product type
        if slots.product_type:
            query = query.where(Product.category.ilike(f"%{slots.product_type}%"))
        
        # Filter by skin type (from attributes JSONB)
        if slots.skin_type:
            # Search in attributes JSONB
            query = query.where(
                Product.attributes.op("?")(f"skin_type_{slots.skin_type}")
            )
        
        # Filter by budget
        if slots.budget_min is not None:
            max_price = slots.budget_max or (slots.budget_min * 1.5)
            query = query.where(
                and_(
                    Product.final_price >= Decimal(str(slots.budget_min)),
                    Product.final_price <= Decimal(str(max_price)),
                )
            )
        
        # Filter by concern
        if slots.concern:
            query = query.where(
                Product.attributes.op("?")(f"concern_{slots.concern}")
            )
        
        # Execute query
        result = await self._db.execute(query.limit(limit))
        products = result.scalars().all()
        
        logger.info(
            "Found %d products for tenant %s with slots %s",
            len(products),
            tenant_id,
            slots.to_dict()
        )
        
        return products

    async def get_product_by_id(
        self,
        tenant_id: UUID,
        product_id: UUID,
    ) -> Optional[Product]:
        """Get product by ID."""
        result = await self._db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
                Product.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_product_by_sku(
        self,
        tenant_id: UUID,
        sku: str,
    ) -> Optional[Product]:
        """Get product by SKU."""
        result = await self._db.execute(
            select(Product).where(
                Product.sku == sku,
                Product.tenant_id == tenant_id,
                Product.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_featured_products(
        self,
        tenant_id: UUID,
        limit: int = 5,
    ) -> list[Product]:
        """Get featured/best-selling products."""
        result = await self._db.execute(
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,
                Product.stock_quantity > 0,
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def get_products_by_category(
        self,
        tenant_id: UUID,
        category: str,
        limit: int = 10,
    ) -> list[Product]:
        """Get products by category."""
        result = await self._db.execute(
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.category.ilike(f"%{category}%"),
                Product.is_active == True,
                Product.stock_quantity > 0,
            )
            .limit(limit)
        )
        return result.scalars().all()


# ── Product Response Formatter ────────────────────────────────────────────────

def format_product_list(products: list[Product], context: str = "") -> str:
    """Format product list for chat response."""
    if not products:
        return "Maaf, saya tidak menemukan produk yang cocok. 😅\n\nMau coba kategori lain?"
    
    response_parts = []
    
    if context:
        response_parts.append(context)
        response_parts.append("")
    
    response_parts.append("Ini rekomendasiku untuk kamu! 🎉\n")
    
    for i, product in enumerate(products, 1):
        price_str = f"Rp {product.final_price:,.0f}"
        if product.discount_price:
            price_str += f" ~~Rp {product.price:,.0f}~~"
        
        stock_str = "✅" if product.is_in_stock else "❌"
        
        response_parts.append(
            f"{i}. *{product.name}* {stock_str}\n"
            f"   {price_str}\n"
            f"   {product.description[:100]}..." if product.description and len(product.description) > 100
            else f"   {product.description or ''}"
        )
        response_parts.append("")
    
    response_parts.append(
        "Mau lihat detail produk mana? Atau langsung pesan? 📦"
    )
    
    return "\n".join(response_parts)


def format_product_detail(product: Product) -> str:
    """Format single product detail for chat response."""
    price_str = f"Rp {product.final_price:,.0f}"
    if product.discount_price:
        price_str += f" (diskon dari Rp {product.price:,.0f})"
    
    stock_status = "✅ Tersedia" if product.is_in_stock else "❌ Stok habis"
    
    response = (
        f"📦 *{product.name}*\n\n"
        f"{product.description or 'Tidak ada deskripsi'}\n\n"
        f"💰 Harga: {price_str}\n"
        f"📦 Stok: {stock_status}\n"
        f"🏷️ SKU: {product.sku}\n"
    )
    
    # Add attributes if available
    if product.attributes:
        attrs = []
        if "skin_type" in product.attributes:
            attrs.append(f"Cocok untuk: {', '.join(product.attributes['skin_type'])}")
        if "benefits" in product.attributes:
            attrs.append(f"Manfaat: {', '.join(product.attributes['benefits'])}")
        
        if attrs:
            response += "\n" + "\n".join(attrs)
    
    response += "\n\nMau pesan produk ini? ✅"
    
    return response
