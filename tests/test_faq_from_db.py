"""Test FAQ matching with proper database loading."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.faq import TenantFAQ
from app.services.intent_router import IntentRouter
import re


async def test_faq_from_db():
    """Test FAQ matching by loading directly from database."""
    
    print("\n" + "=" * 70)
    print("FAQ MATCHING - DIRECT DATABASE LOAD TEST")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # Get tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("❌ No tenant found!")
            return
        
        print(f"\nTesting with tenant: {tenant.name} ({tenant.id})")
        
        # Load FAQs from database
        print("\n[1] Loading FAQs from database...")
        result = await db.execute(
            select(TenantFAQ).where(
                TenantFAQ.tenant_id == tenant.id,
                TenantFAQ.is_active == True
            )
        )
        faqs = result.scalars().all()
        
        print(f"   Found {len(faqs)} FAQs in database")
        
        # Build FAQ patterns manually
        faq_patterns = []
        for faq in faqs:
            for pattern_str in faq.question_patterns:
                try:
                    regex = re.compile(pattern_str, re.IGNORECASE)
                    faq_patterns.append((regex, faq.answer, faq.confidence))
                    print(f"     - Pattern: {pattern_str[:40]}...")
                except re.error as e:
                    print(f"     ❌ Invalid pattern: {pattern_str} - {e}")
        
        print(f"\n   Total patterns: {len(faq_patterns)}")
        
        # Create router with DB patterns
        print("\n[2] Creating Intent Router with DB patterns...")
        router = IntentRouter(faq_patterns=faq_patterns)
        
        # Test FAQ matching
        print("\n[3] Testing FAQ matching...")
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
                print(f"   ❌ No cached answer (went to RAG)")
        
        print("\n" + "=" * 70)
        print("✅ TEST COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_faq_from_db())
