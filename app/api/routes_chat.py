"""Chat routes – send messages and retrieve history."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationListResponse,
    ConversationOut,
    HistoryResponse,
    MessageOut,
)
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.models.message import Message
from app.services.conversation_service import ConversationService
from app.services.rag_service import RAGService
from app.services.sales_rag_service import SalesRAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Process a chat message through the sales RAG pipeline.

    Uses state machine for sales-oriented conversations:
    - INIT → GREETING → ASKING_PRODUCT → ASKING_BUDGET → SHOWING_PRODUCTS → CHECKOUT
    """
    # Use SalesRAGService for stateful conversations
    rag = SalesRAGService(db)
    conv_id = UUID(body.conversation_id) if body.conversation_id else None

    # Get context from RAG if needed (for product info, etc.)
    # For now, we'll let the state machine handle it
    context_from_rag = None

    # For product-related queries, get context from RAG retrieval ONLY (not full response)
    if any(word in body.message.lower() for word in ["produk", "product", "harga", "beli", "pesan"]):
        # Get context from regular RAG service WITHOUT storing messages
        regular_rag = RAGService(db)
        try:
            # Retrieve context only (don't store messages)
            context_from_rag = await regular_rag.retrieve_context(
                query=body.message,
                tenant_id=tenant.id
            )
            # context_from_rag is tuple: (context_text, source_ids)
            context_from_rag = context_from_rag[0] if isinstance(context_from_rag, tuple) else None
            logger.info("Retrieved RAG context for product query: %d chars", len(context_from_rag) if context_from_rag else 0)
        except Exception as e:
            logger.warning("Failed to retrieve RAG context: %s", e)
            context_from_rag = None

    result = await rag.generate_response(
        tenant_id=tenant.id,
        conversation_id=conv_id,
        user_identifier=body.user_identifier,
        user_message=body.message,
        context_from_rag=context_from_rag,
    )

    return ChatResponse(**result)


@router.get("/sessions", response_model=ConversationListResponse)
async def get_sessions(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Retrieve all conversations for the tenant."""
    from app.models.conversation import Conversation
    result = await db.execute(
        select(Conversation)
        .where(Conversation.tenant_id == tenant.id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return ConversationListResponse(
        conversations=[
            ConversationOut(
                id=str(c.id),
                user_identifier=c.user_identifier,
                created_at=c.created_at.isoformat() if c.created_at else None,
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
                summary=c.summary
            )
            for c in conversations
        ]
    )


@router.get("/history/{conversation_id}", response_model=HistoryResponse)
async def get_history(

    conversation_id: UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Retrieve all messages for a conversation."""
    conv_svc = ConversationService(db)
    conv = await conv_svc.get_conversation(conversation_id, tenant.id)

    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation_not_found",
        )

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return HistoryResponse(
        messages=[MessageOut(role=m.role, content=m.content) for m in messages]
    )
