"""Re-ingest dokumen yang tidak punya chunks."""

import asyncio
import os
import sys
import codecs
import uuid

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select, func
from app.db.session import async_session_factory
from app.models.document import Document, Chunk, KnowledgeBase
from app.models.tenant import Tenant
from workers.document_ingest_worker import ingest_document


async def reingest_missing_chunks():
    """Find documents without chunks and re-ingest them."""
    
    print("\n" + "=" * 60)
    print("RE-INGEST DOKUMEN TANPA CHUNKS")
    print("=" * 60)
    
    async with async_session_factory() as db:
        # Get all documents
        docs_result = await db.execute(select(Document))
        docs = docs_result.scalars().all()
        
        print(f"\nTotal dokumen: {len(docs)}")
        
        docs_to_reingest = []
        
        for doc in docs:
            # Count chunks
            chunks_count = await db.execute(
                select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
            )
            chunk_count = chunks_count.scalar() or 0
            
            if chunk_count == 0:
                print(f"\n[MISSING] {doc.file_name} (ID: {doc.id})")
                docs_to_reingest.append(doc)
            else:
                print(f"\n[OK] {doc.file_name} - {chunk_count} chunks")
        
        if not docs_to_reingest:
            print("\n[TIDAK ADA] Semua dokumen sudah punya chunks!")
            return
        
        print(f"\n{'=' * 60}")
        print(f"Dokumen yang perlu di-reingest: {len(docs_to_reingest)}")
        print(f"{'=' * 60}")
        
        # Re-ingest each document
        for doc in docs_to_reingest:
            print(f"\n[PROCESSING] {doc.file_name}...")
            
            # Note: File asli sudah dihapus, jadi kita skip untuk sekarang
            # Ini hanya untuk demonstrasi
            print(f"  [SKIP] File asli sudah tidak ada")
            print(f"  [INFO] Upload ulang file untuk ingest dengan benar")
        
        print("\n" + "=" * 60)
        print("RE-INGEST SELESAI")
        print("=" * 60)
        print("\n[INFO] Untuk upload dokumen baru, gunakan:")
        print("  1. Upload via Swagger UI: POST /api/v1/kb/upload")
        print("  2. Atau manual: python test_pdf_manual.py path/to/file.pdf")


if __name__ == "__main__":
    asyncio.run(reingest_missing_chunks())
