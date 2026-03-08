"""Text chunking for document ingestion."""


def chunk_text(
    text: str,
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[str]:
    """Split *text* into overlapping chunks by character count.

    Uses a simple sliding-window approach.  Each chunk is at most
    *chunk_size* characters, with *overlap* characters shared between
    consecutive chunks.

    Returns a list of non-empty chunk strings.
    """
    if not text or not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        # Try to break at the last sentence-ending punctuation within the window
        if end < text_len:
            slice_ = text[start:end]
            # Look for the last period, question mark, or newline
            for sep in ("\n\n", "\n", ". ", "? ", "! "):
                last_sep = slice_.rfind(sep)
                if last_sep > chunk_size // 2:  # only if it's past midpoint
                    end = start + last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Advance with overlap
        start = end - overlap if end < text_len else text_len

    return chunks
