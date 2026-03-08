"""Tenant FAQ ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TenantFAQ(Base):
    __tablename__ = "tenant_faqs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="FAQ category: business_hours, payment, shipping, etc.",
    )
    question_patterns: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        doc="List of regex patterns for matching questions",
    )
    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Cached answer to return when pattern matches",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.9,
        doc="Confidence threshold (0.0-1.0)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether this FAQ is active",
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )

    # ── relationships ─────────────────────────────────────────────────────
    tenant = relationship("Tenant", back_populates="faqs")

    def to_dict(self) -> dict:
        """Convert FAQ to dictionary for API response."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "category": self.category,
            "question_patterns": self.question_patterns,
            "answer": self.answer,
            "confidence": self.confidence,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
