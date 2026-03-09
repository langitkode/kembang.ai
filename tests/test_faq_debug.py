"""Debug script to test FAQ matching."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.services.intent_router import create_tenant_intent_router


async def test_faq_matching():
    """Test FAQ matching for a tenant."""
    
    print("\n" + "=" * 70)
    print("FAQ MATCHING DEBUG TEST")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # Get tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("❌ No tenant found!")
            return
        
        print(f"\nTesting with tenant: {tenant.name} ({tenant.id})")
        
        # Create intent router
        print("\n[1] Creating tenant intent router...")
        try:
            router = await create_tenant_intent_router(db, tenant.id)
            print(f"✅ Router created successfully!")
            print(f"   FAQ patterns loaded: {len(router._faq_patterns)}")
        except Exception as e:
            print(f"❌ Failed to create router: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test FAQ matching
        print("\n[2] Testing FAQ matching...")
        test_questions = [
            "Jam buka berapa?",
            "Bisa bayar pakai apa?",
            "Ongkir berapa?",
            "Bisa retur nggak?",
        ]
        
        for question in test_questions:
            result = router.classify(question)
            print(f"\n   Q: '{question}'")
            print(f"   Intent: {result.intent.value}")
            print(f"   Confidence: {result.confidence:.0%}")
            if result.cached_answer:
                print(f"   Answer: {result.cached_answer[:80]}...")
            else:
                print(f"   ❌ No cached answer!")
        
        print("\n" + "=" * 70)
        print("✅ FAQ MATCHING TEST COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_faq_matching())
