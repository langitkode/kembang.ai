"""Test chat endpoint dengan PDF yang sudah di-ingest."""

import asyncio
import httpx
import sys
import codecs

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")


async def test_chat_with_pdf():
    """Test RAG pipeline dengan pertanyaan dari PDF content."""
    
    API_BASE = "http://localhost:8000"
    
    print("\n" + "=" * 60)
    print("TEST CHAT DENGAN PDF CONTENT")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Login
        print("\n[1/4] Logging in...")
        login_res = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": "test@kembang.ai", "password": "test123"}
        )
        
        if login_res.status_code != 200:
            print(f"[ERROR] Login failed: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[OK] Login successful")
        
        # 2. Get documents
        print("\n[2/4] Getting documents...")
        docs_res = await client.get(f"{API_BASE}/api/v1/kb/documents", headers=headers)
        
        if docs_res.status_code != 200:
            print(f"[ERROR] Failed to get documents: {docs_res.text}")
            return
        
        docs = docs_res.json()["documents"]
        print(f"[OK] Found {len(docs)} document(s)")
        
        for doc in docs:
            # Get chunk info
            chunks_res = await client.get(
                f"{API_BASE}/api/v1/kb/documents/{doc['id']}/chunks",
                headers=headers
            )
            if chunks_res.status_code == 200:
                chunks_data = chunks_res.json()
                print(f"   - {doc['name']}: {chunks_data.get('chunk_count', 0)} chunks")
        
        # 3. Test questions based on PDF content
        print("\n[3/4] Testing chat with PDF-based questions...")
        print("-" * 60)
        
        questions = [
            "Apa jam operasional toko?",
            "Apakah menerima pembayaran e-wallet?",
            "Apa nama bisnis tenant?",
            "Di mana lokasi toko?",
        ]
        
        conversation_id = None
        
        for i, question in enumerate(questions, 1):
            print(f"\n[Q{i}] {question}")
            
            payload = {
                "message": question,
                "user_identifier": "test-pdf-user"
            }
            
            if conversation_id:
                payload["conversation_id"] = conversation_id
            
            chat_res = await client.post(
                f"{API_BASE}/api/v1/chat/message",
                headers=headers,
                json=payload
            )
            
            if chat_res.status_code != 200:
                print(f"[ERROR] Chat failed: {chat_res.text}")
                continue
            
            result = chat_res.json()
            print(f"[A{i}] {result['reply']}")
            
            if not conversation_id:
                conversation_id = result['conversation_id']
                print(f"   Conversation ID: {conversation_id}")
            
            if result.get('sources'):
                print(f"   Sources: {len(result['sources'])} chunks")
            
            print("-" * 60)
        
        # 4. Test question outside PDF
        print("\n[4/4] Testing question OUTSIDE PDF content...")
        print("-" * 60)
        
        ood_question = "Siapa presiden Indonesia?"
        print(f"\n[Q] {ood_question}")
        
        chat_res = await client.post(
            f"{API_BASE}/api/v1/chat/message",
            headers=headers,
            json={
                "message": ood_question,
                "user_identifier": "test-pdf-user",
                "conversation_id": conversation_id
            }
        )
        
        if chat_res.status_code == 200:
            result = chat_res.json()
            print(f"[A] {result['reply']}")
        else:
            print(f"[ERROR] Chat failed: {chat_res.text}")
        
        print("-" * 60)
    
    print("\n" + "=" * 60)
    print("TEST SELESAI!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_chat_with_pdf())
