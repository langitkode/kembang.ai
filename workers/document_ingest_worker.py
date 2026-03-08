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
                logger.error("❌ Document %s not found", document_id)
                return 0

            # Check file exists BEFORE any processing
            if not file_path:
                logger.error("❌ File path is None for document %s", document_id)
                return 0
                
            if not os.path.exists(file_path):
                logger.error("❌ File path %s does not exist (document %s)", file_path, document_id)
                return 0

            # ── Step 1: Text extraction ───────────────────────────────────────
            logger.info("📄 Extracting text from %s (source_type: %s, size: %d bytes)", 
                       doc.file_name, doc.source_type, os.path.getsize(file_path))
            raw_text = ""

            if doc.source_type == "pdf":
                try:
                    pdf_doc = fitz.open(file_path)
                    logger.info("📕 PDF opened: %d pages", len(pdf_doc))
                    
                    for page_num, page in enumerate(pdf_doc, 1):
                        text = page.get_text()
                        logger.debug("  Page %d: %d characters extracted", page_num, len(text))
                        raw_text += text + "\n"
                    
                    pdf_doc.close()
                    logger.info("✅ PDF text extraction complete: %d total characters", len(raw_text))
                    
                except fitz.FileDataError as e:
                    logger.error("❌ Corrupted PDF: %s - %s", doc.file_name, e)
                    return 0
                except Exception as e:
                    logger.error("❌ PDF extraction error: %s - %s", doc.file_name, e)
                    return 0
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                logger.info("✅ Text file read complete: %d characters", len(raw_text))

            raw_text = raw_text.strip()
            
            if not raw_text:
                logger.warning("⚠️ Extracted text is EMPTY for document %s", doc.id)
                return 0

            logger.info("📊 Extracted text preview (first 200 chars):\n%s", raw_text[:200])

            # ── Step 2: Chunking ──────────────────────────────────────────────
            chunks = chunk_text(
                raw_text,
                chunk_size=settings.CHUNK_SIZE,
                overlap=settings.CHUNK_OVERLAP,
            )
            logger.info("✂️  Created %d chunks from %s", len(chunks), doc.file_name)

            if not chunks:
                logger.warning("⚠️ No chunks created for document %s", doc.id)
                return 0

            # ── Step 3: Embedding ─────────────────────────────────────────────
            logger.info("🧠 Generating embeddings for %d chunks...", len(chunks))
            emb_svc = EmbeddingService()
            embeddings = await emb_svc.embed_documents(chunks)
            logger.info("✅ Embeddings generated: %d vectors", len(embeddings))

            # ── Step 4: Store in DB ───────────────────────────────────────────
            logger.info("💾 Storing chunks in database...")
            for i, (text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = Chunk(
                    document_id=doc.id,
                    content=text,
                    embedding=embedding,
                    chunk_index=i,
                )
                db.add(chunk)

            await db.commit()
            logger.info("✅ SUCCESS: Stored %d chunks for document %s", len(chunks), doc.id)
            return len(chunks)
            
    except Exception as e:
        logger.exception("❌ Error during ingestion of document %s: %s", document_id, e)
        return 0
    finally:
        # Cleanup temporary file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info("🧹 Cleaned up temporary file %s", file_path)
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
