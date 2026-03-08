"""
Test Intent Router - Unit test untuk intent classification dan FAQ caching.
"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.services.intent_router import (
    IntentRouter, 
    IntentType, 
    create_default_router,
    get_intent_router
)


def test_intent_classification():
    """Test intent classification accuracy."""
    
    print("\n" + "=" * 70)
    print("INTENT ROUTER - UNIT TEST")
    print("=" * 70)
    
    router = create_default_router()
    
    test_cases = [
        # (message, expected_intent, description)
        ("Halo", IntentType.GREETING, "Greeting - Halo"),
        ("Selamat pagi", IntentType.GREETING, "Greeting - Selamat pagi"),
        ("Good morning", IntentType.GREETING, "Greeting - Good morning"),
        ("Apa kabar?", IntentType.SMALLTALK, "Smalltalk - Apa kabar"),
        ("Siapa kamu?", IntentType.SMALLTALK, "Smalltalk - Siapa kamu"),
        ("Terima kasih", IntentType.SMALLTALK, "Smalltalk - Thanks"),
        ("Jam buka berapa?", IntentType.FAQ, "FAQ - Jam buka"),
        ("Buka jam berapa?", IntentType.FAQ, "FAQ - Buka jam"),
        ("Hari apa saja buka?", IntentType.FAQ, "FAQ - Hari operasional"),
        ("Bisa bayar pakai apa?", IntentType.FAQ, "FAQ - Metode pembayaran"),
        ("Terima GoPay?", IntentType.FAQ, "FAQ - E-wallet"),
        ("Transfer BCA bisa?", IntentType.FAQ, "FAQ - Bank transfer"),
        ("Ongkir berapa?", IntentType.FAQ, "FAQ - Ongkos kirim"),
        ("Berapa lama sampai?", IntentType.FAQ, "FAQ - Estimasi pengiriman"),
        ("Bisa retur?", IntentType.FAQ, "FAQ - Retur"),
        ("Garansi berapa lama?", IntentType.FAQ, "FAQ - Garansi"),
        ("Kontak CS bagaimana?", IntentType.FAQ, "FAQ - Contact"),
        ("Nomor WhatsApp?", IntentType.FAQ, "FAQ - WhatsApp"),
        ("Alamat toko di mana?", IntentType.FAQ, "FAQ - Lokasi"),
        ("Cabang ada di mana?", IntentType.FAQ, "FAQ - Cabang"),
        ("Harga berapa?", IntentType.FAQ, "FAQ - Harga"),
        ("Ada diskon?", IntentType.FAQ, "FAQ - Promo"),
        ("Katalog lengkap?", IntentType.FAQ, "FAQ - Katalog"),
        ("Stok ada?", IntentType.FAQ, "FAQ - Stok"),
        ("Ready barang?", IntentType.FAQ, "FAQ - Ready stock"),
        ("Cek pesanan 12345", IntentType.TOOL, "Tool - Order status"),
        ("Status order 67890", IntentType.TOOL, "Tool - Order status 2"),
        ("Produk apa yang cocok untuk kulit berminyak?", IntentType.RAG, "RAG - Complex question"),
        ("Saya punya masalah dengan produk yang saya beli kemarin", IntentType.RAG, "RAG - Complex complaint"),
        ("Bandingkan produk A dan B", IntentType.RAG, "RAG - Comparison"),
        ("Cari produk skincare", IntentType.RAG, "RAG - Product search needs context"),
        ("Search product laptop", IntentType.RAG, "RAG - Product search needs context"),
    ]
    
    passed = 0
    failed = 0
    
    print(f"\nTesting {len(test_cases)} cases...\n")
    
    for message, expected_intent, description in test_cases:
        result = router.classify(message)
        
        if result.intent == expected_intent:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        confidence = result.confidence
        cached = "Yes" if result.cached_answer else "No"
        
        print(f"{status}: {description}")
        print(f"       Message: '{message}'")
        print(f"       Expected: {expected_intent.value}, Got: {result.intent.value} (conf: {confidence:.2f}, cached: {cached})")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total:  {len(test_cases)} tests")
    print(f"Passed: {passed} ({100*passed/len(test_cases):.1f}%)")
    print(f"Failed: {failed} ({100*failed/len(test_cases):.1f}%)")
    print("=" * 70)
    
    return failed == 0


def test_faq_answers():
    """Test that FAQ cached answers are appropriate."""
    
    print("\n" + "=" * 70)
    print("FAQ CACHED ANSWERS TEST")
    print("=" * 70)
    
    router = create_default_router()
    
    faq_tests = [
        ("Jam buka berapa?", "09.00", "21.00"),  # Should contain time info
        ("Bayar pakai apa?", "GoPay", "OVO"),  # Should mention e-wallets
        ("Ongkir?", "Indonesia", "hari"),  # Should mention shipping
        ("Retur?", "7 hari", "garansi"),  # Should mention return policy
        ("Kontak?", "WhatsApp", "email"),  # Should mention contact methods
        ("Alamat?", "Jl.", "Jakarta"),  # Should mention address
        ("Harga?", "website", "promo"),  # Should mention where to find prices
        ("Stok?", "ready", "update"),  # Should mention stock info
    ]
    
    passed = 0
    failed = 0
    
    print()
    
    for message, keyword1, keyword2 in faq_tests:
        result = router.classify(message)
        
        if result.intent != IntentType.FAQ:
            print(f"❌ FAIL: '{message}' → Not classified as FAQ (got {result.intent.value})")
            failed += 1
            continue
        
        answer = result.cached_answer or ""
        answer_lower = answer.lower()
        
        if keyword1.lower() in answer_lower or keyword2.lower() in answer_lower:
            print(f"✅ PASS: '{message}'")
            print(f"         Answer contains '{keyword1}' or '{keyword2}'")
            passed += 1
        else:
            print(f"❌ FAIL: '{message}'")
            print(f"         Answer missing keywords '{keyword1}' or '{keyword2}'")
            print(f"         Answer: {answer[:100]}...")
            failed += 1
        print()
    
    print("=" * 70)
    print(f"Passed: {passed}/{len(faq_tests)}")
    print("=" * 70)
    
    return failed == 0


def test_singleton():
    """Test that get_intent_router() returns singleton."""
    
    print("\n" + "=" * 70)
    print("SINGLETON TEST")
    print("=" * 70)
    
    router1 = get_intent_router()
    router2 = get_intent_router()
    
    if router1 is router2:
        print("✅ PASS: get_intent_router() returns same instance")
        return True
    else:
        print("❌ FAIL: get_intent_router() returns different instances")
        return False


async def test_end_to_end():
    """Test full flow with RAG service integration."""
    
    print("\n" + "=" * 70)
    print("END-TO-END INTEGRATION TEST")
    print("=" * 70)
    
    from sqlalchemy import select
    from app.db.session import async_session_factory
    from app.models.tenant import Tenant
    from app.services.rag_service import RAGService
    
    async with async_session_factory() as db:
        # Get test tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("❌ FAIL: No tenant found")
            return False
        
        print(f"Using tenant: {tenant.name} ({tenant.id})")
        
        rag = RAGService(db)
        
        # Test messages
        test_messages = [
            ("Halo", "greeting", False),  # Should NOT use LLM
            ("Jam buka berapa?", "faq", False),  # Should NOT use LLM
            ("Terima kasih", "smalltalk", False),  # Should NOT use LLM
            ("Produk apa yang bagus untuk wajah?", "rag", True),  # Should use LLM
        ]
        
        passed = 0
        failed = 0
        
        for message, expected_intent, expected_llm in test_messages:
            print(f"\nTesting: '{message}'")
            
            result = await rag.generate_response(
                tenant_id=tenant.id,
                conversation_id=None,
                user_identifier="test-intent-router",
                user_message=message,
            )
            
            actual_intent = result.get("intent", "unknown")
            actual_llm = result.get("llm_used", False)
            
            intent_ok = actual_intent == expected_intent
            llm_ok = actual_llm == expected_llm
            
            if intent_ok and llm_ok:
                print(f"  ✅ PASS: intent={actual_intent}, llm_used={actual_llm}")
                passed += 1
            else:
                print(f"  ❌ FAIL: intent={actual_intent} (expected {expected_intent}), llm_used={actual_llm} (expected {expected_llm})")
                failed += 1
            
            print(f"  Reply: {result['reply'][:100]}...")
        
        print("\n" + "=" * 70)
        print(f"Passed: {passed}/{len(test_messages)}")
        print("=" * 70)
        
        return failed == 0


async def main():
    """Run all tests."""
    
    print("\n" + "=" * 70)
    print("INTENT ROUTER - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    # Test 1: Intent classification
    test1 = test_intent_classification()
    
    # Test 2: FAQ answers
    test2 = test_faq_answers()
    
    # Test 3: Singleton
    test3 = test_singleton()
    
    # Test 4: End-to-end
    test4 = await test_end_to_end()
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    all_tests = [
        ("Intent Classification", test1),
        ("FAQ Cached Answers", test2),
        ("Singleton Pattern", test3),
        ("End-to-End Integration", test4),
    ]
    
    for name, passed in all_tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in all_tests)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Intent Router is ready!")
    else:
        print("⚠️  Some tests failed. Review logs above.")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
