"""Tenant ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    api_key: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # ── relationships ─────────────────────────────────────────────────────
    users = relationship(
        "User", back_populates="tenant", lazy="selectin", cascade="all, delete-orphan", passive_deletes=True
    )
    knowledge_bases = relationship(
        "KnowledgeBase",
        back_populates="tenant",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    faqs = relationship(
        "TenantFAQ",
        back_populates="tenant",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    products = relationship(
        "Product",
        back_populates="tenant",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
