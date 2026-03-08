"""Chat routes – send messages and retrieve history."""

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
    
    # For product-related queries, get context from RAG
    if any(word in body.message.lower() for word in ["produk", "product", "harga", "beli", "pesan"]):
        # Fall back to regular RAG for product context
        regular_rag = RAGService(db)
        rag_result = await regular_rag.generate_response(
            tenant_id=tenant.id,
            conversation_id=conv_id,
            user_identifier=body.user_identifier,
            user_message=body.message,
        )
        context_from_rag = rag_result.get("reply")
    
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
