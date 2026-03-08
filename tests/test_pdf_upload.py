"""Quick test script to verify PDF ingestion end-to-end."""

import asyncio
import httpx
import time


async def test_pdf_upload():
    """Test PDF upload and verify chunks are created."""
    
    API_BASE = "http://localhost:8000"
    
    print("\n🧪 PDF Ingestion Test")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Login
        print("\n1️⃣  Logging in...")
        login_res = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": "admin@kembang.ai", "password": "password123"}
        )
        
        if login_res.status_code != 200:
            print(f"❌ Login failed: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # 2. Get user info
        print("\n2️⃣  Getting user info...")
        user_res = await client.get(f"{API_BASE}/api/v1/auth/me", headers=headers)
        if user_res.status_code != 200:
            print(f"❌ Failed to get user info: {user_res.text}")
            return
        
        user_data = user_res.json()
        print(f"✅ User: {user_data['email']}")
        print(f"   Tenant: {user_data['tenant_id']}")
        
        # 3. List existing documents
        print("\n3️⃣  Listing existing documents...")
        docs_res = await client.get(f"{API_BASE}/api/v1/kb/documents", headers=headers)
        if docs_res.status_code != 200:
            print(f"❌ Failed to list documents: {docs_res.text}")
            return
        
        docs = docs_res.json()["documents"]
        print(f"✅ Found {len(docs)} existing document(s)")
        
        # 4. Upload PDF (if exists)
        print("\n4️⃣  Upload a PDF file")
        print("   Please place a test PDF in the current directory")
        print("   and enter the filename, or press Enter to skip.")
        
        pdf_file = input("   PDF filename: ").strip()
        
        if pdf_file:
            import os
            if not os.path.exists(pdf_file):
                print(f"❌ File not found: {pdf_file}")
                return
            
            print(f"   Uploading {pdf_file}...")
            
            with open(pdf_file, "rb") as f:
                upload_res = await client.post(
                    f"{API_BASE}/api/v1/kb/upload",
                    headers=headers,
                    files={"file": (pdf_file, f, "application/pdf")}
                )
            
            if upload_res.status_code != 202:
                print(f"❌ Upload failed: {upload_res.text}")
                return
            
            upload_data = upload_res.json()
            doc_id = upload_data["document_id"]
            print(f"✅ Upload successful!")
            print(f"   Document ID: {doc_id}")
            print(f"   Status: {upload_data['status']}")
            
            # Wait for background processing
            print("\n⏳ Waiting 5 seconds for background processing...")
            await asyncio.sleep(5)
            
            # 5. Check chunks
            print("\n5️⃣  Checking chunks...")
            chunks_res = await client.get(
                f"{API_BASE}/api/v1/kb/documents/{doc_id}/chunks",
                headers=headers
            )
            
            if chunks_res.status_code != 200:
                print(f"❌ Failed to get chunks: {chunks_res.text}")
                return
            
            chunks_data = chunks_res.json()
            print(f"✅ Chunk count: {chunks_data['chunk_count']}")
            
            if chunks_data['chunk_count'] > 0:
                print("\n📊 Sample chunks:")
                for i, chunk in enumerate(chunks_data['sample_chunks'][:2], 1):
                    print(f"\n   --- Chunk {i} ({chunk['content_length']} chars) ---")
                    print(f"   {chunk['content_preview']}")
            else:
                print("❌ No chunks created! Check server logs.")
        
        # 6. Show all documents with chunk counts
        print("\n6️⃣  All documents status:")
        docs_res = await client.get(f"{API_BASE}/api/v1/kb/documents", headers=headers)
        docs = docs_res.json()["documents"]
        
        for doc in docs:
            chunks_res = await client.get(
                f"{API_BASE}/api/v1/kb/documents/{doc['id']}/chunks",
                headers=headers
            )
            chunks_data = chunks_res.json() if chunks_res.status_code == 200 else {"chunk_count": "?"}
            status = "✅" if chunks_data.get("chunk_count", 0) > 0 else "❌"
            print(f"   {status} {doc['name']} ({doc['source_type']}) - {chunks_data.get('chunk_count', '?')} chunks")
    
    print("\n" + "=" * 60)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_pdf_upload())
