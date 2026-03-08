"""Manual PDF ingestion test - bypass FastAPI BackgroundTasks."""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select, func

from app.db.session import async_session_factory
from app.models.document import Document, Chunk, KnowledgeBase
from app.models.tenant import Tenant
from workers.document_ingest_worker import ingest_document


async def test_manual_ingest(pdf_path: str):
    """
    Manually ingest a PDF file for testing.
    
    Usage:
        python test_pdf_manual.py path/to/file.pdf
    """
    pdf_path = Path(pdf_path).resolve()
    
    if not pdf_path.exists():
        print(f"[ERROR] File not found: {pdf_path}")
        return
    
    print(f"\n[TEST] Manual PDF ingestion")
    print(f"   File: {pdf_path.name}")
    print(f"   Size: {pdf_path.stat().st_size} bytes")
    print()
    
    async with async_session_factory() as db:
        # Get or create tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("[ERROR] No tenant found. Please create a tenant first.")
            return
        
        print(f"[OK] Using tenant: {tenant.name} ({tenant.id})")
        
        # Get or create knowledge base
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant.id).limit(1)
        )
        kb = result.scalar_one_or_none()
        
        if not kb:
            kb = KnowledgeBase(tenant_id=tenant.id, name="default")
            db.add(kb)
            await db.flush()
            print(f"[OK] Created knowledge base: {kb.id}")
        else:
            print(f"[OK] Using knowledge base: {kb.name} ({kb.id})")
        
        # Create document record
        doc = Document(
            kb_id=kb.id,
            file_name=pdf_path.name,
            source_type="pdf",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        print(f"[OK] Created document record: {doc.id}")
        print()
        
        # Run ingestion
        print("Starting ingestion...")
        print("=" * 50)
        chunk_count = await ingest_document(doc.id, str(pdf_path))
        print("=" * 50)
        print()
        
        if chunk_count > 0:
            print(f"[OK] SUCCESS: {chunk_count} chunks created!")
            
            # Verify chunks in DB
            result = await db.execute(
                select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
            )
            db_count = result.scalar()
            print(f"[OK] Verified: {db_count} chunks in database")
            
            # Show preview
            print("\nChunk preview:")
            result = await db.execute(
                select(Chunk)
                .where(Chunk.document_id == doc.id)
                .limit(2)
            )
            chunks = result.scalars().all()
            for i, chunk in enumerate(chunks, 1):
                print(f"\n--- Chunk {i} ({len(chunk.content)} chars) ---")
                print(chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content)
        else:
            print("[ERROR] FAILED: No chunks created. Check logs above.")
        
        return chunk_count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pdf_manual.py <path/to/file.pdf>")
        print()
        print("Example:")
        print("  python test_pdf_manual.py documents/test.pdf")
        sys.exit(1)
    
    result = asyncio.run(test_manual_ingest(sys.argv[1]))
    sys.exit(0 if result > 0 else 1)
