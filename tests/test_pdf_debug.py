"""Test script to debug PDF ingestion."""

import asyncio
import uuid
from sqlalchemy import select, func
from app.db.session import async_session_factory
from app.models.document import Document, Chunk, KnowledgeBase
from workers.document_ingest_worker import ingest_document


async def test_pdf_ingestion(document_id: str):
    """Test ingestion for a specific document."""
    doc_uuid = uuid.UUID(document_id)
    
    print(f"\n🔍 Testing ingestion for document: {doc_uuid}")
    
    # Check document exists
    async with async_session_factory() as db:
        doc = await db.get(Document, doc_uuid)
        if not doc:
            print(f"❌ Document {doc_uuid} not found!")
            return
        
        print(f"✅ Document found: {doc.file_name} (source_type: {doc.source_type})")
        
        # Check existing chunks
        result = await db.execute(
            select(func.count(Chunk.id)).where(Chunk.document_id == doc_uuid)
        )
        chunk_count = result.scalar()
        print(f"📊 Existing chunks: {chunk_count}")
        
        if chunk_count > 0:
            # Show sample chunks
            result = await db.execute(
                select(Chunk)
                .where(Chunk.document_id == doc_uuid)
                .limit(3)
            )
            chunks = result.scalars().all()
            print(f"\n📄 Sample chunks:")
            for i, chunk in enumerate(chunks, 1):
                print(f"\n--- Chunk {i} ({len(chunk.content)} chars) ---")
                print(chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content)
    
    # Run ingestion
    print(f"\n🚀 Running ingestion...")
    count = await ingest_document(doc_uuid, None)  # file_path=None to skip file ops if already processed
    print(f"\n✅ Ingestion complete: {count} chunks created")


async def list_all_documents():
    """List all documents and their chunk counts."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Document)
            .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
            .order_by(Document.created_at.desc())
        )
        docs = result.scalars().all()
        
        if not docs:
            print("❌ No documents found!")
            return
        
        print(f"\n📚 Found {len(docs)} document(s):\n")
        
        for doc in docs:
            # Count chunks
            chunk_result = await db.execute(
                select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
            )
            chunk_count = chunk_result.scalar()
            
            status = "✅" if chunk_count > 0 else "❌"
            print(f"{status} {doc.file_name}")
            print(f"   ID: {doc.id}")
            print(f"   Source: {doc.source_type}")
            print(f"   Chunks: {chunk_count}")
            print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test specific document
        asyncio.run(test_pdf_ingestion(sys.argv[1]))
    else:
        # List all documents
        asyncio.run(list_all_documents())
