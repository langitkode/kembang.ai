"""Test hybrid slot extractor with dynamic catalog learning."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.services.catalog_service import CatalogService
from app.services.slot_extractor import SlotExtractor, get_slot_extractor
from app.services.conversation_state_machine import ConversationSlots


async def test_hybrid_extractor():
    """Test hybrid slot extractor with real catalog data."""
    
    print("\n" + "=" * 70)
    print("HYBRID SLOT EXTRACTOR TEST")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # Get first tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("❌ No tenant found!")
            return
        
        print(f"\nTesting with tenant: {tenant.name} ({tenant.id})")
        
        # 1. Load catalog metadata
        print("\n[1] Loading catalog metadata...")
        catalog_service = CatalogService(db)
        metadata = await catalog_service.get_catalog_metadata(tenant.id)
        
        print(f"    Categories: {metadata.get('categories', [])}")
        print(f"    Skin types: {metadata.get('skin_types', [])}")
        print(f"    Concerns: {metadata.get('concerns', [])}")
        print(f"    Price range: {metadata.get('price_range', [])}")
        
        # 2. Test slot extractor WITH catalog metadata
        print("\n[2] Testing slot extractor WITH catalog metadata...")
        extractor_with_catalog = SlotExtractor(metadata)
        
        test_messages = [
            "Cari skincare untuk wajah berminyak",
            "Budget 100ribuan",
            "Yang ada whitening",
            "Serum yang bagus apa?",
        ]
        
        for message in test_messages:
            slots = extractor_with_catalog.extract(message, ConversationSlots())
            print(f"\n    Message: '{message}'")
            print(f"    Extracted: {slots.to_dict()}")
        
        # 3. Test slot extractor WITHOUT catalog (cold start)
        print("\n[3] Testing slot extractor WITHOUT catalog (cold start)...")
        extractor_cold_start = SlotExtractor()
        
        for message in test_messages:
            slots = extractor_cold_start.extract(message, ConversationSlots())
            print(f"\n    Message: '{message}'")
            print(f"    Extracted: {slots.to_dict()}")
        
        # 4. Compare results
        print("\n[4] Comparison:")
        message = "Cari skincare untuk wajah berminyak"
        
        slots_with = extractor_with_catalog.extract(message, ConversationSlots())
        slots_without = extractor_cold_start.extract(message, ConversationSlots())
        
        print(f"\n    Message: '{message}'")
        print(f"    With catalog:    product_type={slots_with.product_type}, skin_type={slots_with.skin_type}")
        print(f"    Cold start:      product_type={slots_without.product_type}, skin_type={slots_without.skin_type}")
        
        if slots_with.product_type == slots_without.product_type:
            print(f"    ✅ Same result (using defaults)")
        else:
            print(f"    🎯 Different! Catalog learned new keywords")
        
        # 5. Test with dynamic category from catalog
        print("\n[5] Testing dynamic category detection...")
        if metadata.get('categories'):
            dynamic_category = metadata['categories'][0]
            message = f"Saya mau {dynamic_category}"
            
            slots = extractor_with_catalog.extract(message, ConversationSlots())
            print(f"    Message: '{message}'")
            print(f"    Detected category: {slots.product_type}")
            
            if slots.product_type:
                print(f"    ✅ Dynamic category detected!")
            else:
                print(f"    ⚠️ Category not detected (expected for some categories)")
        
        print("\n" + "=" * 70)
        print("✅ HYBRID EXTRACTOR TEST COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_hybrid_extractor())
