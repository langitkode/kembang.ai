"""Document ingestion worker.

Processes uploaded documents: extract text → chunk → embed → store in vector DB.

TODO: integrate with a job queue (RQ / Celery).
For now this is a standalone script that can be called directly.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.document import Chunk, Document
from app.rag.chunking import chunk_text
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


import os
import fitz  # PyMuPDF

async def ingest_document(document_id: uuid.UUID, file_path: str = None) -> int:
    """Ingest a document: extract → chunk → embed → store.

    Returns the number of chunks created.
    """
    try:
        async with async_session_factory() as db:
            doc = await db.get(Document, document_id)
            if doc is None:
                logger.error("Document %s not found", document_id)
                return 0

            if not file_path or not os.path.exists(file_path):
                logger.error("File path %s does not exist", file_path)
                return 0

            # ── Step 1: Text extraction ───────────────────────────────────────
            logger.info("Extracting text from %s (source_type: %s)", doc.file_name, doc.source_type)
            raw_text = ""
            
            if doc.source_type == "pdf":
                with fitz.open(file_path) as pdf_doc:
                    for page in pdf_doc:
                        raw_text += page.get_text() + "\n"
            else:
                # Default to reading as plain text for txt, md, website, etc.
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()

            raw_text = raw_text.strip()
            if not raw_text:
                logger.warning("Extracted text is empty for document %s", doc.id)
                return 0

            # ── Step 2: Chunking ──────────────────────────────────────────────
            chunks = chunk_text(
                raw_text,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            logger.info("Created %d chunks from %s", len(chunks), doc.file_name)

            if not chunks:
                return 0

            # ── Step 3: Embedding ─────────────────────────────────────────────
            emb_svc = EmbeddingService()
            embeddings = await emb_svc.embed_documents(chunks)

            # ── Step 4: Store in DB ───────────────────────────────────────────
            for text, embedding in zip(chunks, embeddings):
                chunk = Chunk(
                    document_id=doc.id,
                    content=text,
                    embedding=embedding,
                )
                db.add(chunk)

            await db.commit()
            logger.info("Stored %d chunks for document %s", len(chunks), doc.id)
            return len(chunks)
    except Exception as e:
        logger.exception("Error during ingestion of document %s: %s", document_id, e)
        return 0
    finally:
        # Cleanup temporary file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info("Cleaned up temporary file %s", file_path)
            except OSError as e:
                logger.error("Failed to delete temp file %s: %s", file_path, e)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m workers.document_ingest_worker <document_id>")
        sys.exit(1)

    doc_id = uuid.UUID(sys.argv[1])
    count = asyncio.run(ingest_document(doc_id))
    print(f"Ingested {count} chunks.")
