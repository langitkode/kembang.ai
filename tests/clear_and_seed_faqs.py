"""Clear and re-seed FAQs for all tenants."""

import asyncio
from sqlalchemy import select, delete
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.faq import TenantFAQ


# Import DEFAULT_FAQS from seed_faqs
DEFAULT_FAQS = [
    {
        "category": "business_hours",
        "patterns": ["jam buka berapa", "buka jam berapa", "hari apa saja buka", "operasional kapan"],
        "answer": "Kami buka setiap hari pukul 09.00–21.00 WIB.",
        "confidence": 0.9,
    },
    {
        "category": "payment",
        "patterns": ["bisa bayar pakai apa", "metode pembayaran", "terima gopay", "transfer bca"],
        "answer": "Kami menerima pembayaran via E-wallet dan Transfer Bank.",
        "confidence": 0.9,
    },
    {
        "category": "shipping",
        "patterns": ["ongkir berapa", "pengiriman berapa lama", "pakai ekspedisi apa"],
        "answer": "Pengiriman tersedia ke seluruh Indonesia.",
        "confidence": 0.85,
    },
    {
        "category": "returns",
        "patterns": ["bisa retur", "garansi berapa lama", "barang rusak"],
        "answer": "Retur dalam 7 hari setelah diterima.",
        "confidence": 0.85,
    },
    {
        "category": "contact",
        "patterns": ["hubungi cs", "nomor whatsapp", "email support"],
        "answer": "Hubungi kami via WhatsApp atau Email.",
        "confidence": 0.9,
    },
    {
        "category": "location",
        "patterns": ["lokasi toko", "alamat", "cabang"],
        "answer": "Alamat kami: Jl. Raya Utama No. 123, Jakarta Selatan.",
        "confidence": 0.85,
    },
    {
        "category": "pricing",
        "patterns": ["harga berapa", "ada diskon", "promo"],
        "answer": "Cek website untuk harga lengkap.",
        "confidence": 0.8,
    },
    {
        "category": "stock",
        "patterns": ["stok ada", "ready", "preorder"],
        "answer": "Stok update real-time di website.",
        "confidence": 0.85,
    },
]


async def clear_and_seed():
    """Clear all FAQs and re-seed for all tenants."""
    
    print("\nClearing all FAQs...")
    async with async_session_factory() as db:
        await db.execute(delete(TenantFAQ))
        await db.commit()
        print("✅ All FAQs cleared")
        
        # Get all tenants
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        
        print(f"\nFound {len(tenants)} tenant(s)")
        
        # Seed FAQs for each tenant
        for tenant in tenants:
            print(f"\nSeeding FAQs for: {tenant.name}")
            
            count = 0
            for faq_data in DEFAULT_FAQS:
                faq = TenantFAQ(
                    tenant_id=tenant.id,
                    category=faq_data["category"],
                    question_patterns=faq_data["patterns"],
                    answer=faq_data["answer"],
                    confidence=faq_data["confidence"],
                    is_active=True,
                )
                db.add(faq)
                count += 1
            
            await db.commit()
            print(f"   Added {count} FAQs")
        
        print("\n✅ FAQ SEEDING COMPLETED")


if __name__ == "__main__":
    asyncio.run(clear_and_seed())
