"""Chat routes – send messages and retrieve history."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.schemas import ChatRequest, ChatResponse, HistoryResponse, MessageOut
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.models.message import Message
from app.services.conversation_service import ConversationService
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Process a chat message through the RAG pipeline."""
    rag = RAGService(db)
    conv_id = UUID(body.conversation_id) if body.conversation_id else None

    result = await rag.generate_response(
        tenant_id=tenant.id,
        conversation_id=conv_id,
        user_identifier=body.user_identifier,
        user_message=body.message,
    )

    return ChatResponse(**result)


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
