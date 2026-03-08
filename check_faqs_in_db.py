"""Check if FAQs exist in database."""

import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.faq import TenantFAQ


async def check_faqs():
    async with async_session_factory() as db:
        result = await db.execute(select(TenantFAQ))
        faqs = result.scalars().all()
        
        print(f"\nFAQs in database: {len(faqs)}")
        
        if faqs:
            print("\nFirst 5 FAQs:")
            for i, faq in enumerate(faqs[:5], 1):
                print(f"  {i}. Category: {faq.category}")
                print(f"     Patterns: {faq.question_patterns}")
                print(f"     Answer: {faq.answer[:80]}...")
                print()
        else:
            print("\n⚠️  NO FAQs IN DATABASE!")
            print("\nThis explains why FAQ matching is not working.")
            print("\nTo add FAQs:")
            print("  1. Use API: POST /api/v1/faq")
            print("  2. Or use Swagger UI at /docs")
            print("  3. Or run SQL INSERT directly")


if __name__ == "__main__":
    asyncio.run(check_faqs())
