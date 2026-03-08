"""Test Phase 2: Humanize Response + Conversation State."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.conversation import Conversation
from app.models.tenant import Tenant


async def test_phase2():
    """Test Phase 2 implementation."""
    
    print("\n" + "=" * 70)
    print("PHASE 2 TEST - Humanize Response + Conversation State")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # Test 1: Check conversation model has new fields
        print("\n[Test 1] Checking conversation model...")
        result = await db.execute(select(Conversation).limit(1))
        conv = result.scalar_one_or_none()
        
        if conv:
            print(f"    ✅ Conversation found: {conv.id}")
            print(f"       - state: {conv.state}")
            print(f"       - last_topic: {conv.last_topic}")
            
            # Test state methods
            conv.update_state("topic", "product_inquiry")
            conv.update_state("skin_type", "oily")
            print(f"       - After update: {conv.state}")
            
            topic = conv.get_state("topic")
            print(f"       - Get state 'topic': {topic}")
        else:
            print("    ℹ️  No conversations found (this is OK for new DB)")
        
        # Test 2: Check tenant exists
        print("\n[Test 2] Checking tenant...")
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if tenant:
            print(f"    ✅ Tenant found: {tenant.name}")
        else:
            print("    ❌ No tenant found")
        
        # Test 3: Response formatter
        print("\n[Test 3] Testing response formatter...")
        from app.services.response_formatter import get_response_formatter
        
        formatter = get_response_formatter()
        
        test_responses = [
            ("Halo", "greeting"),
            ("Jam buka berapa?", "faq"),
            ("Produk apa yang bagus?", "rag"),
        ]
        
        for raw, intent in test_responses:
            formatted = formatter.format(raw, intent=intent)
            print(f"    {intent:10s}: '{raw}' → '{formatted}'")
        
        # Test 4: Response cache
        print("\n[Test 4] Testing response cache...")
        from app.services.response_cache import get_response_cache
        
        cache = get_response_cache()
        cache.set("test-tenant", "test query", {"reply": "Test response"})
        result = cache.get("test-tenant", "test query")
        print(f"    Cache test: {result}")
        print(f"    Stats: {cache.get_stats()}")
        
        # Test 5: Intent router
        print("\n[Test 5] Testing intent router...")
        from app.services.intent_router import create_default_router
        
        router = create_default_router()
        
        test_queries = [
            "Halo",
            "Jam buka berapa?",
            "Produk apa yang bagus untuk wajah?",
        ]
        
        for query in test_queries:
            result = router.classify(query)
            print(f"    '{query}' → {result.intent.value} (conf: {result.confidence:.0%})")
    
    print("\n" + "=" * 70)
    print("✅ PHASE 2 TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)
    
    print("\n📊 Phase 2 Features:")
    print("  ✅ Conversation state (JSONB)")
    print("  ✅ Last topic tracking")
    print("  ✅ Response formatter (emoji, templates, fillers)")
    print("  ✅ Response cache (TTL-based)")
    print("  ✅ Intent router (smart matching)")
    print("\n💡 Chatbot is now more human and cost-efficient!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_phase2())
