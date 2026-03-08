"""Knowledge-base routes – upload documents and list them."""

import os
import shutil
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.schemas import DocumentListResponse, DocumentOut
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.models.document import Document, KnowledgeBase
from workers.document_ingest_worker import ingest_document

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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

    # Enqueue background task
    background_tasks.add_task(ingest_document, doc.id, file_path)

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
