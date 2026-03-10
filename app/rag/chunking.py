"""Text chunking for document ingestion with token-based semantic boundaries."""

import tiktoken


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens in text using tiktoken."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 128,
) -> list[str]:
    """Split text into overlapping chunks by token count with semantic boundaries.

    Uses a semantic-aware approach:
    1. Split by paragraph boundaries first (\n\n)
    2. If paragraph too large, split by sentence boundaries (. ! ?)
    3. If sentence still too large, hard split at token limit

    Args:
        text: Input text to chunk
        chunk_size: Target tokens per chunk (default 512)
        overlap: Overlap in tokens between consecutive chunks (default 128)

    Returns:
        List of chunk strings, each approximately chunk_size tokens
    """
    if not text or not text.strip():
        return []

    try:
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")

    chunks: list[str] = []

    # Step 1: Split into paragraphs
    paragraphs = text.split("\n\n")
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    current_chunk: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        # Split paragraph into sentences if too large
        sentences = _split_into_sentences(paragraph)

        for sentence in sentences:
            sentence_tokens = len(enc.encode(sentence))

            # If single sentence exceeds chunk_size, hard split
            if sentence_tokens > chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Hard split the long sentence
                hard_splits = _hard_split_sentence(sentence, chunk_size, enc)
                chunks.extend(hard_splits[:-1])  # All but last
                current_chunk = [hard_splits[-1]]  # Keep last for continuation
                current_tokens = len(enc.encode(hard_splits[-1]))

            # If adding this sentence exceeds limit, save chunk and start new
            elif current_tokens + sentence_tokens > chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    # Start new chunk with overlap
                    overlap_start = max(0, len(current_chunk) - _estimate_overlap_sentences(current_chunk, overlap))
                    current_chunk = current_chunk[overlap_start:]
                    current_tokens = sum(len(enc.encode(s)) for s in current_chunk)

                current_chunk.append(sentence)
                current_tokens += sentence_tokens

            # Otherwise, add to current chunk
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # Post-process: merge very small chunks
    chunks = _merge_small_chunks(chunks, enc, min_tokens=100)

    return chunks


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using common delimiters."""
    import re

    # Split on sentence-ending punctuation followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _hard_split_sentence(sentence: str, max_tokens: int, enc) -> list[str]:
    """Hard split a long sentence at token boundaries."""
    tokens = enc.encode(sentence)
    chunks: list[str] = []

    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        # Try to end at word boundary
        if i + max_tokens < len(tokens):
            # Find last space in decoded chunk
            chunk_text = enc.decode(chunk_tokens)
            last_space = chunk_text.rfind(' ')
            if last_space > max_tokens // 2:
                chunk_text = chunk_text[:last_space]
                # Put remaining tokens back
                remaining = enc.encode(chunk_text[last_space:])
                tokens = tokens[:i + max_tokens] + remaining
        else:
            chunk_text = enc.decode(chunk_tokens)

        if chunk_text.strip():
            chunks.append(chunk_text.strip())

    return chunks


def _estimate_overlap_sentences(sentences: list[str], target_overlap: int) -> int:
    """Estimate how many sentences to keep for overlap."""
    try:
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")

    overlap_sentences = 0
    overlap_tokens = 0

    for sentence in reversed(sentences):
        overlap_tokens += len(enc.encode(sentence))
        overlap_sentences += 1
        if overlap_tokens >= target_overlap:
            break

    return overlap_sentences


def _merge_small_chunks(chunks: list[str], enc, min_tokens: int = 100) -> list[str]:
    """Merge chunks that are too small."""
    if len(chunks) <= 1:
        return chunks

    merged: list[str] = []
    current = chunks[0]
    current_tokens = len(enc.encode(current))

    for chunk in chunks[1:]:
        chunk_tokens = len(enc.encode(chunk))

        if current_tokens < min_tokens:
            # Merge with next
            current += " " + chunk
            current_tokens += chunk_tokens
        else:
            # Save current and start new
            merged.append(current)
            current = chunk
            current_tokens = chunk_tokens

    if current:
        merged.append(current)

    return merged
