"""RAG service – orchestrates the full retrieval-augmented generation pipeline.

Flow: query → embedding → hybrid retrieval → rerank → context build → LLM.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.context_builder import build_context
from app.rag.reranker import rerank
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.usage_service import UsageService


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a customer service assistant for SMEs. "
    "Answer using the provided context only. "
    "Do not hallucinate. "
    "If the answer is not in the context, say 'Maaf, informasi tidak tersedia.'"
)


class RAGService:
    """End-to-end RAG orchestrator."""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._embedding = EmbeddingService()
        self._retrieval = RetrievalService(db)
        self._llm = LLMService()
        self._usage = UsageService(db)
        self._conversation = ConversationService(db)

    # ── Public API ────────────────────────────────────────────────────────

    async def generate_response(
        self,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        user_identifier: str,
        user_message: str,
    ) -> dict:
        """Process a user message through the full RAG pipeline.

        Returns::

            {
                "conversation_id": "...",
                "reply": "...",
                "sources": ["chunk-id-1", ...],
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

        # 3. Retrieve context
        context_text, source_ids = await self.retrieve_context(
            user_message, tenant_id
        )

        # 4. Build prompt with conversation history
        messages = await self.build_prompt(conv.id, user_message, context_text)

        # 5. Generate LLM response
        llm_result = await self._llm.generate(messages)

        # 6. Store assistant message
        await self._conversation.add_message(
            conv.id, "assistant", llm_result["content"], llm_result["output_tokens"]
        )

        # 7. Log usage
        await self._usage.log_usage(
            tenant_id=tenant_id,
            model=llm_result["model"],
            input_tokens=llm_result["input_tokens"],
            output_tokens=llm_result["output_tokens"],
        )

        return {
            "conversation_id": str(conv.id),
            "reply": llm_result["content"],
            "sources": source_ids,
        }

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
