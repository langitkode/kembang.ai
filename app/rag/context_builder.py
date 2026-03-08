"""Context builder – assemble retrieved chunks into a prompt-ready string."""

import tiktoken

from app.core.config import settings
from app.models.document import Chunk


def build_context(
    chunks: list[Chunk],
    max_tokens: int | None = None,
) -> str:
    """Concatenate chunk contents up to the token limit.

    Returns a single string suitable for insertion into a prompt template.
    """
    max_tokens = max_tokens or settings.MAX_CONTEXT_TOKENS

    # Use the tiktoken encoder matching the default model
    try:
        enc = tiktoken.encoding_for_model(settings.DEFAULT_LLM_MODEL)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")

    parts: list[str] = []
    token_count = 0

    for i, chunk in enumerate(chunks, start=1):
        chunk_tokens = len(enc.encode(chunk.content))
        if token_count + chunk_tokens > max_tokens:
            break
        parts.append(f"[{i}] {chunk.content}")
        token_count += chunk_tokens

    return "\n\n".join(parts)
