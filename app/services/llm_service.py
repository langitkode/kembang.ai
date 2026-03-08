"""LLM service – centralized access to language model APIs.

All LLM calls MUST go through this service (coding rule #8).
"""

import logging
import litellm

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Centralized LLM gateway with model routing."""

    def __init__(self):
        # We no longer need an OpenAI client instance; LiteLLM covers routing.
        pass

    # ── Generation ────────────────────────────────────────────────────────

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict:
        """Send a chat completion request and return a structured result.

        Returns::

            {
                "content": "...",
                "model": "gpt-4o-mini",
                "input_tokens": 123,
                "output_tokens": 45,
            }
        """
        model = model or self.route_model(messages)

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            # LiteLLM automatically picks up OPENAI_API_KEY or GROQ_API_KEY from env
        )

        choice = response.choices[0]
        usage = response.usage

        return {
            "content": choice.message.content or "",
            "model": response.model,
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        }

    # ── Streaming ─────────────────────────────────────────────────────────

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ):
        """Yield content chunks from a streaming chat completion.

        Note: token counts are not available during streaming; the caller
        should estimate usage separately if needed.
        """
        model = model or self.route_model(messages)

        stream = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    # ── Model routing ─────────────────────────────────────────────────────

    def route_model(self, messages: list[dict[str, str]]) -> str:
        """Choose model based on input complexity.

        Simple heuristic: if total message length < 500 chars → small model,
        otherwise fallback model.
        """
        total_chars = sum(len(m.get("content", "")) for m in messages)
        if total_chars < 500:
            return settings.DEFAULT_LLM_MODEL
        return settings.FALLBACK_LLM_MODEL
