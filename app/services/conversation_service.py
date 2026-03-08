"""Conversation service – create, read, and manage chat conversations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message


class ConversationService:
    """Handles conversation lifecycle and message persistence."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Create ────────────────────────────────────────────────────────────

    async def create_conversation(
        self, tenant_id: uuid.UUID, user_identifier: str
    ) -> Conversation:
        """Start a new conversation for *user_identifier* under *tenant_id*."""
        conv = Conversation(
            tenant_id=tenant_id,
            user_identifier=user_identifier,
        )
        self._db.add(conv)
        await self._db.commit()
        await self._db.refresh(conv)
        return conv

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_conversation(
        self, conversation_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Conversation | None:
        """Return the conversation if it belongs to *tenant_id*."""
        result = await self._db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    # ── Messages ──────────────────────────────────────────────────────────

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        tokens_used: int | None = None,
    ) -> Message:
        """Persist a single message in the conversation."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
        )
        self._db.add(msg)
        await self._db.commit()
        await self._db.refresh(msg)
        return msg

    async def get_recent_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int | None = None,
    ) -> list[Message]:
        """Return the *limit* most recent messages, oldest-first."""
        limit = limit or settings.HISTORY_LIMIT
        result = await self._db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()  # oldest first
        return messages

    # ── History compression ───────────────────────────────────────────────

    async def summarize_history(
        self,
        conversation_id: uuid.UUID,
        summary_text: str,
    ) -> None:
        """Store a running summary on the conversation record."""
        conv = await self._db.get(Conversation, conversation_id)
        if conv:
            conv.summary = summary_text
            conv.updated_at = datetime.now(timezone.utc)
            await self._db.commit()
