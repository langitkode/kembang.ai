"""RAG service – orchestrates the full retrieval-augmented generation pipeline.

Flow: query → intent classification → [FAQ cache | Tool | RAG] → LLM (if needed).
"""

import uuid
import logging
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.context_builder import build_context
from app.rag.reranker import rerank
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.usage_service import UsageService
from app.services.intent_router import get_intent_router, IntentType, IntentRouter, create_tenant_intent_router
from app.services.response_cache import get_response_cache
from app.services.response_formatter import get_response_formatter
from app.tools.tool_router import execute_tool

logger = logging.getLogger(__name__)


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a customer service assistant for SMEs. "
    "Answer using the provided context only. "
    "Do not hallucinate. "
    "If the answer is not in the context, say 'Maaf, informasi tidak tersedia.'"
)


class RAGService:
    """End-to-end RAG orchestrator with intelligent intent routing."""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._embedding = EmbeddingService()
        self._retrieval = RetrievalService(db)
        self._llm = LLMService()
        self._usage = UsageService(db)
        self._conversation = ConversationService(db)
        self._intent_router = None  # Lazy-loaded per tenant
        self._tenant_routers: dict[uuid.UUID, IntentRouter] = {}  # Cache per tenant
        self._response_cache = get_response_cache()  # Global response cache
        self._formatter = get_response_formatter()  # Response formatter

    async def _get_intent_router(self, tenant_id: uuid.UUID) -> IntentRouter:
        """Get or create intent router for specific tenant (lazy-loaded from DB)."""
        # Check cache first
        if tenant_id in self._tenant_routers:
            return self._tenant_routers[tenant_id]
        
        # Load from database
        router = await create_tenant_intent_router(self._db, tenant_id)
        self._tenant_routers[tenant_id] = router
        
        logger.info("Loaded intent router for tenant %s with %d FAQ patterns", tenant_id, len(router._faq_patterns))
        return router

    # ── Public API ────────────────────────────────────────────────────────

    async def generate_response(
        self,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        user_identifier: str,
        user_message: str,
    ) -> dict:
        """Process a user message through intelligent intent routing.

        Routing logic:
        1. FAQ → Return cached answer (NO LLM)
        2. Tool → Execute tool (NO LLM)
        3. Greeting/Smalltalk → Return cached response (NO LLM)
        4. RAG → Full pipeline with LLM

        Returns::

            {
                "conversation_id": "...",
                "reply": "...",
                "sources": ["chunk-id-1", ...],
                "intent": "faq|tool|rag|greeting|smalltalk",
                "llm_used": True|False,
            }
        """
        # 1. Ensure conversation exists
        if conversation_id:
            conv = await self._conversation.get_conversation(
                conversation_id, tenant_id
            )
        else:
            conv = None

        if conv is None:
            conv = await self._conversation.create_conversation(
                tenant_id, user_identifier
            )

        # 2. Store user message
        await self._conversation.add_message(conv.id, "user", user_message)

        # 3. NEW: Get tenant-specific intent router and classify intent
        intent_router = await self._get_intent_router(tenant_id)
        intent_result = intent_router.classify(user_message)
        logger.info(
            "Intent classification: %s (confidence: %.2f) for message: %s",
            intent_result.intent.value,
            intent_result.confidence,
            user_message[:50]
        )

        # 4. Route based on intent
        if intent_result.intent == IntentType.FAQ:
            # FAQ: Return cached answer, NO LLM
            logger.info("FAQ match: Returning cached answer")
            
            # Format response to be more human
            formatted_response = self._formatter.format(
                intent_result.cached_answer,
                intent="faq"
            )
            
            await self._conversation.add_message(
                conv.id, "assistant", formatted_response
            )
            return {
                "conversation_id": str(conv.id),
                "reply": formatted_response,
                "sources": [],
                "intent": "faq",
                "llm_used": False,
            }

        elif intent_result.intent == IntentType.GREETING:
            # Greeting: Return formatted cached response, NO LLM
            logger.info("Greeting detected: Returning cached response")
            
            # Format with time-based greeting
            formatted_response = self._formatter.format(
                intent_result.cached_answer,
                intent="greeting"
            )
            
            await self._conversation.add_message(
                conv.id, "assistant", formatted_response
            )
            return {
                "conversation_id": str(conv.id),
                "reply": formatted_response,
                "sources": [],
                "intent": "greeting",
                "llm_used": False,
            }

        elif intent_result.intent == IntentType.SMALLTALK:
            # Smalltalk: Return formatted cached response, NO LLM
            logger.info("Smalltalk detected: Returning cached response")
            
            formatted_response = self._formatter.format(
                intent_result.cached_answer,
                intent="smalltalk"
            )
            
            await self._conversation.add_message(
                conv.id, "assistant", formatted_response
            )
            return {
                "conversation_id": str(conv.id),
                "reply": formatted_response,
                "sources": [],
                "intent": "smalltalk",
                "llm_used": False,
            }

        elif intent_result.intent == IntentType.TOOL:
            # Tool: Execute tool function, NO LLM
            tool_name = intent_result.payload.get("tool_name")
            tool_params = intent_result.payload.get("params", {})
            logger.info("Tool trigger: %s with params %s", tool_name, tool_params)
            
            tool_result = await execute_tool(tool_name, tool_params)
            
            if "error" in tool_result:
                # Fallback to RAG if tool fails
                logger.warning("Tool execution failed, falling back to RAG")
                return await self._generate_rag_response(
                    conv, user_message, tenant_id
                )
            
            reply = self._format_tool_response(tool_result)
            await self._conversation.add_message(conv.id, "assistant", reply)
            return {
                "conversation_id": str(conv.id),
                "reply": reply,
                "sources": [],
                "intent": "tool",
                "llm_used": False,
            }

        else:
            # RAG: Full pipeline with LLM
            # First, check response cache
            cache_key = f"{tenant_id}:{hashlib.sha256(user_message.lower().encode()).hexdigest()[:16]}"
            cached_response = self._response_cache.get(tenant_id, user_message)
            
            if cached_response:
                logger.info("Response cache HIT: Returning cached LLM response")
                # Store message in conversation
                await self._conversation.add_message(
                    conv.id, "assistant", cached_response["reply"]
                )
                return {
                    "conversation_id": str(conv.id),
                    "reply": cached_response["reply"],
                    "sources": cached_response.get("sources", []),
                    "intent": "rag_cached",
                    "llm_used": False,
                    "from_cache": True,
                }
            
            logger.info("Response cache MISS: Using RAG pipeline")
            return await self._generate_rag_response(
                conv, user_message, tenant_id, cache_key
            )

    async def _generate_rag_response(
        self,
        conv,
        user_message: str,
        tenant_id: uuid.UUID,
        cache_key: str = None,
    ) -> dict:
        """Full RAG pipeline with LLM (existing logic)."""
        # Retrieve context
        context_text, source_ids = await self.retrieve_context(
            user_message, tenant_id
        )

        # Build prompt with conversation history
        messages = await self.build_prompt(conv.id, user_message, context_text)

        # Generate LLM response
        llm_result = await self._llm.generate(messages)
        raw_response = llm_result["content"]

        # Format response to be more human
        formatted_response = self._formatter.format(
            raw_response,
            intent="rag",
            context={"is_first_message": False}
        )

        # Store assistant message (store formatted version)
        await self._conversation.add_message(
            conv.id, "assistant", formatted_response, llm_result["output_tokens"]
        )

        # Log usage
        await self._usage.log_usage(
            tenant_id=tenant_id,
            model=llm_result["model"],
            input_tokens=llm_result["input_tokens"],
            output_tokens=llm_result["output_tokens"],
        )

        # Cache the response (if cache_key provided)
        if cache_key:
            response_data = {
                "reply": formatted_response,  # Cache formatted version
                "sources": source_ids,
            }
            self._response_cache.set(tenant_id, user_message, response_data)
            logger.info("Cached LLM response for future identical queries")

        return {
            "conversation_id": str(conv.id),
            "reply": formatted_response,
            "sources": source_ids,
            "intent": "rag",
            "llm_used": True,
        }

    def _format_tool_response(self, tool_result: dict) -> str:
        """Format tool execution result into human-readable response."""
        if "error" in tool_result:
            return f"Maaf, terjadi kesalahan: {tool_result['error']}"
        
        # Format based on tool type
        if "product_name" in tool_result:
            # Product lookup result
            return (
                f"📦 *{tool_result.get('product_name')}*\n"
                f"Harga: Rp {tool_result.get('price', 'N/A'):,}\n"
                f"Stok: {tool_result.get('stock', 'N/A')}\n"
                f"Deskripsi: {tool_result.get('description', 'N/A')}"
            )
        elif "order_id" in tool_result:
            # Order status result
            status_emoji = {
                "pending": "⏳",
                "processing": "🔄",
                "shipped": "📦",
                "delivered": "✅",
                "cancelled": "❌"
            }
            emoji = status_emoji.get(tool_result.get("status", ""), "📋")
            return (
                f"{emoji} *Order #{tool_result.get('order_id')}*\n"
                f"Status: {tool_result.get('status', 'N/A').upper()}\n"
                f"Ekspedisi: {tool_result.get('courier', 'N/A')}\n"
                f"Resi: {tool_result.get('tracking', 'N/A')}"
            )
        else:
            # Generic format
            return "\n".join(f"{k}: {v}" for k, v in tool_result.items())

    # ── Pipeline steps ────────────────────────────────────────────────────

    async def retrieve_context(
        self, query: str, tenant_id: uuid.UUID
    ) -> tuple[str, list[str]]:
        """Embed → hybrid search → rerank → build context string."""
        query_embedding = await self._embedding.embed_query(query)

        chunks = await self._retrieval.hybrid_search(
            query_embedding, query, tenant_id
        )

        # Rerank top chunks
        reranked = await rerank(query, chunks, top_k=settings.RERANK_TOP_K)

        # Build context
        context_text = build_context(
            reranked, max_tokens=settings.MAX_CONTEXT_TOKENS
        )
        source_ids = [str(c.id) for c in reranked]

        return context_text, source_ids

    async def build_prompt(
        self,
        conversation_id: uuid.UUID,
        user_message: str,
        context: str,
    ) -> list[dict[str, str]]:
        """Assemble the message list for the LLM call."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
        ]

        # Include conversation summary if available
        from app.models.conversation import Conversation as ConvModel

        conv = await self._db.get(ConvModel, conversation_id)
        if conv and conv.summary:
            messages.append(
                {"role": "system", "content": f"Conversation summary: {conv.summary}"}
            )

        # Recent history
        recent = await self._conversation.get_recent_messages(conversation_id)
        for msg in recent[:-1]:  # exclude the just-added user message
            messages.append({"role": msg.role, "content": msg.content})

        # Context + current question
        messages.append(
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {user_message}",
            }
        )

        return messages
