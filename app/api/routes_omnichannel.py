"""Omnichannel Webhook routes – handle incoming messages from external platforms (WhatsApp, Telegram, etc)."""

import uuid
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.dependencies import DBSession
from app.services.rag_service import RAGService

router = APIRouter()
logger = logging.getLogger(__name__)

class WebhookResponse(BaseModel):
    status: str = "ok"
    message_id: Optional[str] = None
    reply: Optional[str] = None

class GenericWebhookBody(BaseModel):
    """A generic structure for custom external integrations."""
    user_id: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

@router.post("/{tenant_id}/{platform}", response_model=WebhookResponse)
async def omnichannel_webhook(
    tenant_id: uuid.UUID,
    platform: str,
    request: Request,
    db: DBSession,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Receive messages from various platforms.
    
    Platforms supported (conceptually):
    - whatsapp: Meta Webhook
    - telegram: Telegram Bot API
    - generic: Simple JSON structure
    """
    body = await request.json()
    logger.info("Received %s webhook for tenant %s", platform, tenant_id)

    # 1. Platform-specific parsing logic
    user_identifier = "unknown"
    user_message = ""
    
    if platform == "whatsapp":
        # Meta (WhatsApp) Structure: body["entry"][0]["changes"][0]["value"]["messages"][0]
        try:
            msg_data = body["entry"][0]["changes"][0]["value"]["messages"][0]
            user_identifier = msg_data["from"]  # Phone number
            user_message = msg_data["text"]["body"]
        except (KeyError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid WhatsApp payload")
            
    elif platform == "telegram":
        # Telegram Structure: body["message"]["from"]["id"]
        try:
            msg_data = body["message"]
            user_identifier = str(msg_data["from"]["id"])
            user_message = msg_data["text"]
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid Telegram payload")
            
    else:
        # Generic fallback
        try:
            user_identifier = body.get("user_id", "default-user")
            user_message = body.get("message", "")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid generic payload")

    if not user_message:
        return WebhookResponse(status="ignored", reply="No message content")

    # 2. Call RAG Service
    rag = RAGService(db)
    try:
        # In a real omnichannel setup, we might want to manage persistent conversation_ids 
        # based on the platform + user_identifier (e.g., in a lookup table).
        # For v1, we let RAGService handle it or start a new one if not provided.
        result = await rag.generate_response(
            tenant_id=tenant_id,
            conversation_id=None, # RAGService will auto-create or we could look it up
            user_identifier=f"{platform}:{user_identifier}",
            user_message=user_message,
        )
        
        return WebhookResponse(
            status="ok",
            message_id=result.get("conversation_id"),
            reply=result.get("answer")
        )
    except Exception as e:
        logger.error("Error processing omnichannel message: %s", e)
        raise HTTPException(status_code=500, detail="Intelligence service error")
