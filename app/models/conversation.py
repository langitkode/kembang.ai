"""Conversation ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="End-user identifier (e.g. phone, session id)"
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Running summary of older messages"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # ── relationships ─────────────────────────────────────────────────────
    messages = relationship(
        "Message", back_populates="conversation", order_by="Message.created_at"
    )
