"""Widget routes – public endpoints for website integration."""

import uuid

from fastapi import APIRouter

from app.api.schemas import ChatRequest, ChatResponse
from app.core.dependencies import DBSession, WidgetTenant
from app.services.rag_service import RAGService

router = APIRouter(prefix="/widget", tags=["widget"])


@router.post("/chat", response_model=ChatResponse)
async def widget_chat(
    body: ChatRequest,
    db: DBSession,
    tenant: WidgetTenant,
):
    """Process a chat message using the Tenant's API Key.
    
    This endpoint does not require a JWT, making it safe for public frontend clients
    (e.g., website chat widgets) to call directly using the X-API-Key header.
    """
    rag = RAGService(db)
    conv_id = uuid.UUID(body.conversation_id) if body.conversation_id else None

    result = await rag.generate_response(
        tenant_id=tenant.id,
        conversation_id=conv_id,
        user_identifier=body.user_identifier,
        user_message=body.message,
    )

    return ChatResponse(**result)
