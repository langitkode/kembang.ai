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
            response_text, new_state = self._state_handler.handle_state(
                state=state,
                user_message=user_message,
                context_from_rag=context_from_rag,
            )
        except Exception as e:
            logger.exception("Error in state handler: %s", e)
            # Fallback to simple response
            response_text = "Maaf, terjadi kesalahan. Bisa ulangi pertanyaan kamu?"
            new_state = state
            new_state.stage = ConversationStage.GREETING_DONE
        
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
