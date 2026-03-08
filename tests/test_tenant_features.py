"""
Comprehensive test untuk Tenant App features:
1. Upload PDF
2. Verify ingestion
3. Chat/Playground
4. Conversation history
"""

import asyncio
import sys
import codecs
import os
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

import httpx


async def test_tenant_features():
    """Full test suite untuk tenant app."""
    
    API_BASE = "http://localhost:8000"
    
    print("\n" + "=" * 70)
    print("TENANT APP - COMPREHENSIVE FEATURE TEST")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # ─────────────────────────────────────────────────────────────────────
        # STEP 1: Login
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 1] Login...")
        login_res = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": "test@kembang.ai", "password": "test123"}
        )
        
        if login_res.status_code != 200:
            print(f"[ERROR] Login failed: {login_res.text}")
            print("[INFO] Make sure user exists: python create_test_user.py")
            return False
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[OK] Login successful")
        
        # Get user info
        user_res = await client.get(f"{API_BASE}/api/v1/auth/me", headers=headers)
        user = user_res.json()
        print(f"     User: {user['email']}")
        print(f"     Tenant: {user['tenant_id']}")
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 2: Create test PDF
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 2] Creating test PDF...")
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        os.makedirs("uploads", exist_ok=True)
        test_pdf = "uploads/tenant_test_doc.pdf"
        
        c = canvas.Canvas(test_pdf, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 72, "Tenant Test Document")
        
        c.setFont("Helvetica", 12)
        y = height - 120
        
        content = [
            "Dokumen ini untuk testing fitur Tenant App.",
            "",
            "Informasi Perusahaan:",
            "1. Nama: PT Teknologi Nusantara",
            "2. Lokasi: Bandung, Jawa Barat",
            "3. Produk: Chatbot AI untuk UMKM",
            "4. Harga: Mulai dari Rp 150.000/bulan",
            "",
            "Fitur Unggulan:",
            "- Auto-reply WhatsApp",
            "- Knowledge Base RAG",
            "- Analytics Dashboard",
            "- Multi-language support (ID/EN)",
            "",
            "Kontak Support:",
            "Email: support@nusantara.co.id",
            "WhatsApp: +62 812-3456-7890",
            "Website: www.nusantara.co.id",
        ]
        
        for line in content:
            c.drawString(72, y, line)
            y -= 20
        
        c.save()
        print(f"[OK] PDF created: {test_pdf}")
        print(f"    Size: {os.path.getsize(test_pdf)} bytes")
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 3: Upload PDF
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 3] Uploading PDF to Knowledge Base...")
        
        with open(test_pdf, "rb") as f:
            upload_res = await client.post(
                f"{API_BASE}/api/v1/kb/upload",
                headers=headers,
                files={"file": ("tenant_test_doc.pdf", f, "application/pdf")}
            )
        
        if upload_res.status_code != 202:
            print(f"[ERROR] Upload failed: {upload_res.text}")
            return False
        
        upload_data = upload_res.json()
        doc_id = upload_data["document_id"]
        print(f"[OK] Upload successful!")
        print(f"    Document ID: {doc_id}")
        print(f"    Status: {upload_data['status']}")
        
        # Wait for background processing
        print("\n[WAIT] Waiting 10 seconds for ingestion...")
        await asyncio.sleep(10)
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 4: Verify Ingestion
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 4] Verifying document ingestion...")
        
        chunks_res = await client.get(
            f"{API_BASE}/api/v1/kb/documents/{doc_id}/chunks",
            headers=headers
        )
        
        if chunks_res.status_code != 200:
            print(f"[ERROR] Failed to get chunks: {chunks_res.text}")
            return False
        
        chunks_data = chunks_res.json()
        chunk_count = chunks_data.get("chunk_count", 0)
        
        if chunk_count == 0:
            print(f"[ERROR] No chunks created!")
            return False
        
        print(f"[OK] Ingestion successful!")
        print(f"    Chunks created: {chunk_count}")
        print(f"\n    Sample chunks:")
        for i, chunk in enumerate(chunks_data.get("sample_chunks", [])[:2], 1):
            preview = chunk["content_preview"][:100].replace('\n', ' ')
            print(f"      [{i}] {preview}...")
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 5: Test Chat/Playground
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 5] Testing Chat/Playground...")
        print("-" * 70)
        
        test_questions = [
            "Apa nama perusahaan?",
            "Di mana lokasi kantor?",
            "Berapa harga produk?",
            "Bagaimana cara kontak support?",
            "Apakah ada fitur WhatsApp?",
        ]
        
        conversation_id = None
        correct_answers = 0
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n[Q{i}] {question}")
            
            payload = {
                "message": question,
                "user_identifier": "tenant-test-user"
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
            answer = result["reply"]
            sources = result.get("sources", [])
            
            print(f"[A{i}] {answer}")
            print(f"     Sources: {len(sources)} chunks")
            
            if not conversation_id:
                conversation_id = result["conversation_id"]
                print(f"     Conversation ID: {conversation_id}")
            
            # Check if answer is from context (not "Maaf, informasi tidak tersedia")
            if "maaf" not in answer.lower() or "tidak tersedia" not in answer.lower():
                correct_answers += 1
            
            print("-" * 70)
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 6: Test Conversation History
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 6] Testing Conversation History...")
        
        history_res = await client.get(
            f"{API_BASE}/api/v1/chat/history/{conversation_id}",
            headers=headers
        )
        
        if history_res.status_code != 200:
            print(f"[ERROR] Failed to get history: {history_res.text}")
            return False
        
        history_data = history_res.json()
        messages = history_data.get("messages", [])
        
        print(f"[OK] Conversation history retrieved!")
        print(f"    Total messages: {len(messages)}")
        print(f"    Conversation ID: {conversation_id}")
        
        # ─────────────────────────────────────────────────────────────────────
        # STEP 7: List All Documents
        # ─────────────────────────────────────────────────────────────────────
        print("\n[STEP 7] Listing all documents...")
        
        docs_res = await client.get(
            f"{API_BASE}/api/v1/kb/documents",
            headers=headers
        )
        
        if docs_res.status_code != 200:
            print(f"[ERROR] Failed to list documents: {docs_res.text}")
            return False
        
        docs_data = docs_res.json()
        docs = docs_data.get("documents", [])
        
        print(f"[OK] Found {len(docs)} document(s):")
        for doc in docs:
            print(f"    - {doc['name']} ({doc['source_type']})")
        
        # ─────────────────────────────────────────────────────────────────────
        # SUMMARY
        # ─────────────────────────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        tests_passed = [
            ("Login", True),
            ("Create PDF", True),
            ("Upload PDF", True),
            ("Document Ingestion", chunk_count > 0),
            ("Chat/Playground", correct_answers >= 3),
            ("Conversation History", len(messages) > 0),
            ("List Documents", len(docs) > 0),
        ]
        
        for test_name, passed in tests_passed:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        all_passed = all(passed for _, passed in tests_passed)
        
        print("\n" + "=" * 70)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Tenant app is ready!")
        else:
            print("⚠️  Some tests failed. Check logs above.")
        print("=" * 70)
        
        # Cleanup
        print("\n[CLEANUP] Removing test PDF...")
        if os.path.exists(test_pdf):
            os.remove(test_pdf)
            print(f"[OK] Removed {test_pdf}")
        
        return all_passed


if __name__ == "__main__":
    result = asyncio.run(test_tenant_features())
    sys.exit(0 if result else 1)
