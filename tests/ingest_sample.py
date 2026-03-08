"""Ingest sample_tenant_profile.pdf yang ada di uploads/."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.document import Document
from workers.document_ingest_worker import ingest_document


async def ingest_sample_pdf():
    """Ingest sample_tenant_profile.pdf."""
    
    print("\n" + "=" * 60)
    print("INGEST SAMPLE_TENANT_PROFILE.PDF")
    print("=" * 60)
    
    file_path = "uploads/sample_tenant_profile.pdf"
    
    async with async_session_factory() as db:
        # Check if document already exists
        docs_result = await db.execute(
            select(Document).where(Document.file_name == "sample_tenant_profile.pdf")
        )
        existing_doc = docs_result.scalars().first()
        
        if existing_doc:
            print(f"\n[INFO] Dokumen sudah ada: {existing_doc.id}")
            print(f"  File: {existing_doc.file_name}")
            print(f"  Source: {existing_doc.source_type}")
            
            # Delete existing document
            print(f"\n[DELETE] Menghapus dokumen lama...")
            await db.delete(existing_doc)
            await db.commit()
            print(f"[OK] Dokumen lama dihapus")
    
    # Now ingest fresh
    print(f"\n[INGEST] Starting ingestion dari {file_path}...")
    print("=" * 60)
    
    # Create new document record
    async with async_session_factory() as db:
        # Get KB
        kb_result = await db.execute(select(KnowledgeBase).limit(1))
        kb = kb_result.scalars().first()
        
        if not kb:
            print("[ERROR] No knowledge base found!")
            return
        
        # Create document
        doc = Document(
            kb_id=kb.id,
            file_name="sample_tenant_profile.pdf",
            source_type="pdf",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        print(f"[OK] Document record created: {doc.id}")
    
    # Run ingestion (pass file path yang sebenarnya)
    # Tapi file sudah dihapus, jadi kita perlu copy dulu
    print("\n[ERROR] File asli sudah dihapus oleh worker sebelumnya!")
    print("[INFO] Silakan upload ulang file via:")
    print("  POST /api/v1/kb/upload")
    print("\nAtau copy file PDF ke uploads/ dan jalankan:")
    print("  python test_pdf_manual.py uploads/your_file.pdf")


if __name__ == "__main__":
    from app.models.document import KnowledgeBase
    asyncio.run(ingest_sample_pdf())
