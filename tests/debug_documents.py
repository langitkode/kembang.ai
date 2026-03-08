"""Debug script untuk cek dokumen dan chunks di DB."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select, func
from app.db.session import async_session_factory
from app.models.document import Document, Chunk, KnowledgeBase
from app.models.tenant import Tenant
from app.models.user import User


async def debug_documents():
    """Check all documents and chunks in the database."""
    
    print("\n" + "=" * 60)
    print("DEBUG: DOCUMENTS AND CHUNKS IN DATABASE")
    print("=" * 60)
    
    async with async_session_factory() as db:
        # List all tenants
        print("\n[TENANTS]")
        tenants_result = await db.execute(select(Tenant))
        tenants = tenants_result.scalars().all()
        
        for tenant in tenants:
            print(f"\n  Tenant: {tenant.name} ({tenant.id})")
            
            # List users
            users_result = await db.execute(
                select(User).where(User.tenant_id == tenant.id)
            )
            users = users_result.scalars().all()
            print(f"    Users: {len(users)}")
            for u in users:
                print(f"      - {u.email} ({u.role})")
            
            # List knowledge bases
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant.id)
            )
            kbs = kb_result.scalars().all()
            
            for kb in kbs:
                print(f"\n    Knowledge Base: {kb.name} ({kb.id})")
                
                # List documents
                docs_result = await db.execute(
                    select(Document).where(Document.kb_id == kb.id)
                )
                docs = docs_result.scalars().all()
                
                for doc in docs:
                    # Count chunks
                    chunks_count = await db.execute(
                        select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
                    )
                    chunk_count = chunks_count.scalar() or 0
                    
                    print(f"\n      Document: {doc.file_name}")
                    print(f"        ID: {doc.id}")
                    print(f"        Source Type: {doc.source_type}")
                    print(f"        Chunks: {chunk_count}")
                    
                    # Show first chunk preview
                    if chunk_count > 0:
                        chunks_result = await db.execute(
                            select(Chunk).where(Chunk.document_id == doc.id).limit(1)
                        )
                        first_chunk = chunks_result.scalar_one_or_none()
                        if first_chunk:
                            preview = first_chunk.content[:150].replace('\n', ' ')
                            print(f"        Preview: {preview}...")


if __name__ == "__main__":
    asyncio.run(debug_documents())
