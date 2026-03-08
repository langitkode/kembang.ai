"""End-to-end test: Upload PDF -> Ingest -> Chat."""

import asyncio
import sys
import codecs
import os

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.document import Document, KnowledgeBase
from workers.document_ingest_worker import ingest_document


async def test_e2e():
    """Full test: create PDF -> ingest -> verify chunks."""
    
    print("\n" + "=" * 60)
    print("END-TO-END TEST: PDF UPLOAD -> INGEST -> CHUNKS")
    print("=" * 60)
    
    file_path = "uploads/test_e2e.pdf"
    
    # Step 1: Create test PDF
    print("\n[STEP 1] Creating test PDF...")
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    os.makedirs("uploads", exist_ok=True)
    
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Test Document for RAG")
    
    c.setFont("Helvetica", 12)
    y = height - 120
    
    content = [
        "Ini adalah dokumen test untuk sistem RAG (Retrieval-Augmented Generation).",
        "",
        "Informasi Penting:",
        "",
        "1. Perusahaan kami bernama PT Teknologi Maju Indonesia.",
        "2. Kantor pusat berlokasi di Jakarta Selatan, Indonesia.",
        "3. Produk unggulan: Chatbot AI untuk UMKM.",
        "4. Harga paket mulai dari Rp 99.000 per bulan.",
        "5. Support tersedia 24/7 via WhatsApp dan email.",
        "",
        "Kontak:",
        "Email: info@majuindo.co.id",
        "Telepon: +62 21 5555 1234",
    ]
    
    for line in content:
        c.drawString(72, y, line)
        y -= 20
    
    c.save()
    print(f"[OK] PDF created: {file_path}")
    print(f"    Size: {os.path.getsize(file_path)} bytes")
    
    # Step 2: Create document record in DB
    print("\n[STEP 2] Creating document record...")
    async with async_session_factory() as db:
        # Get KB
        kb_result = await db.execute(select(KnowledgeBase).limit(1))
        kb = kb_result.scalars().first()
        
        if not kb:
            print("[ERROR] No knowledge base found!")
            return False
        
        doc = Document(
            kb_id=kb.id,
            file_name="test_e2e.pdf",
            source_type="pdf",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        doc_id = doc.id
        print(f"[OK] Document created: {doc_id}")
    
    # Step 3: Run ingestion
    print("\n[STEP 3] Running ingestion...")
    print("=" * 60)
    chunk_count = await ingest_document(doc_id, file_path)
    print("=" * 60)
    
    # Step 4: Verify
    print("\n[STEP 4] Verifying chunks...")
    async with async_session_factory() as db:
        from sqlalchemy import func
        from app.models.document import Chunk
        
        result = await db.execute(
            select(func.count(Chunk.id)).where(Chunk.document_id == doc_id)
        )
        db_count = result.scalar() or 0
        
        print(f"[OK] Chunks in DB: {db_count}")
        
        if db_count > 0:
            # Show preview
            chunks_result = await db.execute(
                select(Chunk).where(Chunk.document_id == doc_id).limit(2)
            )
            chunks = chunks_result.scalars().all()
            
            print("\n[PREVIEW] Sample chunks:")
            for i, chunk in enumerate(chunks, 1):
                preview = chunk.content[:150].replace('\n', ' ')
                print(f"  Chunk {i}: {preview}...")
    
    print("\n" + "=" * 60)
    if chunk_count > 0 and db_count > 0:
        print("TEST RESULT: SUCCESS")
        print(f"  - {chunk_count} chunks created")
        print(f"  - {db_count} chunks verified in DB")
    else:
        print("TEST RESULT: FAILED")
        print(f"  - chunk_count: {chunk_count}")
        print(f"  - db_count: {db_count}")
    print("=" * 60)
    
    return chunk_count > 0 and db_count > 0


if __name__ == "__main__":
    result = asyncio.run(test_e2e())
    sys.exit(0 if result else 1)
