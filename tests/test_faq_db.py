"""Test script to verify FAQ database and API."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select, func
from app.db.session import async_session_factory
from app.models.faq import TenantFAQ
from app.models.tenant import Tenant


async def test_faq_db():
    """Test FAQ database operations."""
    
    print("\n" + "=" * 70)
    print("FAQ DATABASE TEST")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # 1. Check if tenant_faqs table exists
        print("\n[1] Checking tenant_faqs table...")
        try:
            result = await db.execute(select(func.count(TenantFAQ.id)))
            count = result.scalar()
            print(f"    ✅ Table exists, {count} FAQs found")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return False
        
        # 2. List tenants
        print("\n[2] Listing tenants...")
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        print(f"    Found {len(tenants)} tenant(s):")
        for t in tenants:
            print(f"      - {t.name} ({t.id})")
        
        # 3. Check FAQ per tenant
        print("\n[3] FAQ per tenant:")
        for tenant in tenants:
            result = await db.execute(
                select(func.count(TenantFAQ.id)).where(TenantFAQ.tenant_id == tenant.id)
            )
            faq_count = result.scalar() or 0
            print(f"      - {tenant.name}: {faq_count} FAQ")
        
        # 4. Create sample FAQ for first tenant
        if tenants:
            print("\n[4] Creating sample FAQ for first tenant...")
            tenant = tenants[0]
            
            # Check if FAQ already exists
            result = await db.execute(
                select(TenantFAQ).where(TenantFAQ.tenant_id == tenant.id).limit(1)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"    ℹ️  FAQ already exists for this tenant")
            else:
                faq = TenantFAQ(
                    tenant_id=tenant.id,
                    category="business_hours",
                    question_patterns=["jam buka berapa", "buka jam berapa", "hari apa buka"],
                    answer="Kami buka setiap hari pukul 09.00–21.00 WIB.",
                    confidence=0.9,
                    is_active=True,
                )
                db.add(faq)
                await db.commit()
                print(f"    ✅ Created sample FAQ for {tenant.name}")
            
            # Verify
            result = await db.execute(
                select(func.count(TenantFAQ.id)).where(TenantFAQ.tenant_id == tenant.id)
            )
            faq_count = result.scalar() or 0
            print(f"    Total FAQ for {tenant.name}: {faq_count}")
        
        print("\n" + "=" * 70)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        return True


if __name__ == "__main__":
    result = asyncio.run(test_faq_db())
    sys.exit(0 if result else 1)
