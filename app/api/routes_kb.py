"""Knowledge-base routes – upload documents and list them."""

import os
import shutil
import uuid
import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.schemas import DocumentListResponse, DocumentOut
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.models.document import Document, KnowledgeBase
from workers.document_ingest_worker import ingest_document
from app.services.intent_router import get_intent_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _process_document_background(document_id: uuid.UUID, file_path: str):
    """Wrapper to properly handle async ingestion in background."""
    try:
        await ingest_document(document_id, file_path)
    except Exception as e:
        # Log error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Background ingestion failed: %s", e)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Upload a document to the tenant's default knowledge base.

    The actual ingestion (text extraction, chunking, embedding) is handled
    asynchronously by the document ingest worker.
    """
    # Ensure a default knowledge base exists
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant.id).limit(1)
    )
    kb = result.scalar_one_or_none()

    if kb is None:
        kb = KnowledgeBase(tenant_id=tenant.id, name="default")
        db.add(kb)
        await db.flush()

    # Determine source type from file extension
    filename = file.filename or "unknown.txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "text"
    source_type_map = {"pdf": "pdf", "html": "website", "txt": "text", "md": "text"}
    source_type = source_type_map.get(ext, "text")

    doc = Document(
        kb_id=kb.id,
        file_name=filename,
        source_type=source_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Save file temporarily for background processing
    temp_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, temp_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Enqueue background task with proper async handling
    background_tasks.add_task(_process_document_background, doc.id, file_path)

    return {"document_id": str(doc.id), "status": "processing"}


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """List all documents across the tenant's knowledge bases."""
    result = await db.execute(
        select(Document)
        .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
        .where(KnowledgeBase.tenant_id == tenant.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentOut(id=str(d.id), name=d.file_name, source_type=d.source_type)
            for d in docs
        ]
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Delete a document and its associated chunks/embeddings."""
    # Find the document and verify it belongs to the current tenant
    result = await db.execute(
        select(Document)
        .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
        .where(Document.id == document_id)
        .where(KnowledgeBase.tenant_id == tenant.id)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document_not_found",
        )

    # In a real system, you'd also want to delete the actual vector embeddings
    # from pgvector and any local files.
    await db.delete(doc)
    await db.commit()
    return None


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Get chunk count and preview for a document (debug endpoint)."""
    from sqlalchemy import func
    from app.models.document import Chunk
    
    # Find the document
    result = await db.execute(
        select(Document)
        .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
        .where(Document.id == document_id)
        .where(KnowledgeBase.tenant_id == tenant.id)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document_not_found",
        )

    # Count chunks
    chunk_count_result = await db.execute(
        select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    )
    chunk_count = chunk_count_result.scalar() or 0

    # Get sample chunks
    sample_chunks = []
    if chunk_count > 0:
        chunks_result = await db.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .limit(5)
        )
        chunks = chunks_result.scalars().all()
        sample_chunks = [
            {
                "index": c.chunk_index,
                "content_preview": c.content[:200] + "..." if len(c.content) > 200 else c.content,
                "content_length": len(c.content),
            }
            for c in chunks
        ]

    return {
        "document_id": str(doc.id),
        "file_name": doc.file_name,
        "source_type": doc.source_type,
        "chunk_count": chunk_count,
        "sample_chunks": sample_chunks,
    }


# ── FAQ Management ────────────────────────────────────────────────────────────


@router.get("/faq")
async def list_faq(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """List all FAQ patterns for the current tenant.
    
    Note: Currently using global FAQ router. Tenant-specific FAQ
    customization can be added in future iterations.
    """
    router = get_intent_router()
    
    # Return FAQ info (in production, this would come from DB)
    return {
        "faq_count": len(router._faq_patterns),
        "message": "FAQ management is currently using global patterns. Tenant-specific FAQ coming soon.",
    }


@router.post("/faq")
async def add_faq(
    body: dict,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Add a new FAQ pattern for the current tenant.
    
    Request body:
    {
        "patterns": ["jam buka", "buka jam berapa"],  # List of trigger phrases
        "answer": "Kami buka setiap hari pukul 09.00-21.00 WIB",
        "confidence": 0.9  # Optional, default 0.9
    }
    
    Note: This is a runtime-only addition (not persisted to DB yet).
    """
    patterns = body.get("patterns", [])
    answer = body.get("answer", "")
    confidence = body.get("confidence", 0.9)
    
    if not patterns or not answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patterns and answer are required",
        )
    
    router = get_intent_router()
    router.add_faq(patterns, answer, confidence)
    
    return {
        "message": f"Added FAQ with {len(patterns)} patterns",
        "patterns": patterns,
        "answer": answer,
        "confidence": confidence,
    }


@router.delete("/faq/{pattern_id}")
async def delete_faq(
    pattern_id: int,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Delete an FAQ pattern by index.
    
    Note: Currently not implemented for global router.
    This is a placeholder for future tenant-specific FAQ management.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="FAQ deletion not yet implemented. Coming soon.",
    )
