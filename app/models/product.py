"""Product ORM model for sales catalog."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,  # Removed unique=True - SKU is unique per tenant, not globally
        doc="Stock Keeping Unit - unique product identifier",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Product category (skincare, makeup, bodycare, haircare)",
    )
    subcategory: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Product subcategory (serum, toner, moisturizer, etc.)",
    )
    
    # Pricing
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Product price in IDR",
    )
    discount_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Discounted price (if on sale)",
    )
    
    # Inventory
    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Available stock quantity",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="Whether product is available for sale",
    )
    
    # Product attributes (flexible JSONB for skin type, concerns, etc.)
    attributes: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Product attributes (skin_type, benefits, ingredients, etc.)",
    )
    
    # Images
    images: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="List of image URLs",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )

    # ── relationships ─────────────────────────────────────────────────────
    tenant = relationship("Tenant", back_populates="products")

    def to_dict(self) -> dict:
        """Convert product to dictionary for API response."""
        return {
            "id": str(self.id),
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "price": float(self.price),
            "discount_price": float(self.discount_price) if self.discount_price else None,
            "stock_quantity": self.stock_quantity,
            "is_active": self.is_active,
            "attributes": self.attributes,
            "images": self.images,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def final_price(self) -> Decimal:
        """Get final price (discount if available)."""
        return self.discount_price if self.discount_price else self.price
    
    @property
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.stock_quantity > 0 and self.is_active
