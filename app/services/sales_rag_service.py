"""Sales-oriented RAG service with conversation state machine.

Flow: 
1. Get conversation state
2. Extract slots from user message
3. Transition to new state based on intent + slots
4. Generate state-specific response
5. Update conversation state
"""

import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.conversation_service import ConversationService
from app.services.conversation_state_machine import ConversationState, ConversationStage
from app.services.slot_extractor import get_slot_extractor
from app.services.state_handlers import StateHandler
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)


class SalesRAGService:
    """Sales-oriented RAG service with state machine."""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._conversation = ConversationService(db)
        self._usage = UsageService(db)
        self._slot_extractor = None  # Will be initialized per tenant
        self._state_handler = None  # Will be initialized per tenant

    async def generate_response(
        self,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        user_identifier: str,
        user_message: str,
        context_from_rag: str | None = None,
    ) -> dict:
        """Generate response using sales state machine.
        
        Args:
            tenant_id: Tenant identifier
            conversation_id: Conversation ID (or None for new)
            user_identifier: User identifier
            user_message: User message
            context_from_rag: Optional context from RAG retrieval
        
        Returns:
            Response dict with conversation_id, reply, etc.
        """
        # 1. Get or create conversation
        if conversation_id:
            conv = await self._conversation.get_conversation(conversation_id, tenant_id)
        else:
            conv = None
        
        if conv is None:
            conv = await self._conversation.create_conversation(tenant_id, user_identifier)
        
        # 2. Initialize state handler with tenant context (lazy loading)
        if self._state_handler is None or not self._state_handler._initialized:
            self._state_handler = StateHandler(db=self._db, tenant_id=tenant_id)
            await self._state_handler.initialize()
        
        # 3. Get conversation state
        state = ConversationState.from_dict(conv.state or {})
        
        # 4. Store user message
        await self._conversation.add_message(conv.id, "user", user_message)
        
        # 5. Handle state transition and get response
        try:
            logger.debug("Calling state handler with state: %s, message: %s", state.stage.value, user_message[:50])
            
            response_text, new_state = self._state_handler.handle_state(
                state=state,
                user_message=user_message,
                context_from_rag=context_from_rag,
            )
            
            logger.debug("State handler returned: %s, new_state: %s", response_text[:50] if response_text else "None", new_state.stage.value)
            
        except Exception as e:
            logger.exception("❌ Error in state handler: %s", e)
            logger.error("State: %s, Message: %s, Context: %s", state.stage.value, user_message[:100], context_from_rag[:100] if context_from_rag else None)
            
            # Only use fallback for critical errors
            # For normal errors, try to continue with RAG
            if "catalog" in str(e).lower() or "database" in str(e).lower() or "async" in str(e).lower():
                # Database/catalog error - use simple response
                logger.warning("Critical error, using fallback response")
                response_text = "Maaf, saya sedang mengalami gangguan. Bisa coba lagi?"
                new_state = state
                new_state.stage = ConversationStage.GREETING_DONE
            else:
                # Other errors - try RAG fallback
                logger.warning("Non-critical error, falling back to RAG: %s", e)
                return await self._generate_rag_response(
                    conv, user_message, tenant_id
                )

        # 6. Update conversation state
        conv.state = new_state.to_dict()
        await self._db.commit()

        # 7. Store assistant response
        await self._conversation.add_message(conv.id, "assistant", response_text)

        logger.info(
            "State transition: %s → %s (slots: %s)",
            state.stage.value,
            new_state.stage.value,
            new_state.slots.to_dict()
        )

        return {
            "conversation_id": str(conv.id),
            "reply": response_text,
            "sources": [],
            "intent": new_state.stage.value,
            "state": new_state.to_dict(),
            "llm_used": context_from_rag is not None,
        }

    async def _generate_rag_response(
        self,
        conv,
        user_message: str,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Fallback to RAG pipeline with LLM when state handler fails.
        
        Args:
            conv: Conversation object
            user_message: User message
            tenant_id: Tenant identifier
            
        Returns:
            Response dict with conversation_id, reply, sources, etc.
        """
        from app.services.rag_service import RAGService
        
        # Create a temporary RAG service for fallback
        rag_service = RAGService(db=self._db)
        
        # Use RAG service to generate response
        return await rag_service.generate_response(
            tenant_id=tenant_id,
            conversation_id=conv.id,
            user_identifier=conv.user_identifier,
            user_message=user_message,
        )
