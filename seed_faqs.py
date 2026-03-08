"""Seed FAQs for all tenants."""

import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.faq import TenantFAQ


# Default FAQs for all tenants
DEFAULT_FAQS = [
    {
        "category": "business_hours",
        "patterns": [
            "jam buka berapa",
            "buka jam berapa",
            "hari apa saja buka",
            "operasional kapan",
            "tutup jam berapa",
            "jam berapa buka",
        ],
        "answer": "Kami buka setiap hari pukul 09.00–21.00 WIB.",
        "confidence": 0.9,
    },
    {
        "category": "payment",
        "patterns": [
            "bisa bayar pakai apa",
            "metode pembayaran apa saja",
            "terima goPay",
            "terima ovo",
            "terima dana",
            "bisa transfer bca",
            "bisa cod",
            "bayar di tempat",
        ],
        "answer": "Kami menerima pembayaran via:\n• E-wallet: GoPay, OVO, Dana, ShopeePay\n• Transfer Bank: BCA, Mandiri, BNI, BRI\n• COD (Bayar di Tempat) untuk area tertentu",
        "confidence": 0.9,
    },
    {
        "category": "shipping",
        "patterns": [
            "ongkir berapa",
            "pengiriman berapa lama",
            "pakai ekspedisi apa",
            "bisa kirim ke surabaya",
            "ongkos kirim",
            "gratis ongkir",
        ],
        "answer": "Pengiriman tersedia ke seluruh Indonesia:\n• Jabodetabek: 1-2 hari\n• Jawa: 2-4 hari\n• Luar Jawa: 3-7 hari\n\nOngkir dihitung otomatis saat checkout.",
        "confidence": 0.85,
    },
    {
        "category": "returns",
        "patterns": [
            "bisa retur",
            "cara retur bagaimana",
            "garansi berapa lama",
            "barang rusak bisa tukar",
            "kebijakan retur",
        ],
        "answer": "Kebijakan retur:\n• Retur dalam 7 hari setelah diterima\n• Barang harus dalam kondisi asli\n• Foto/video unboxing sebagai bukti\n• Garansi resmi 1 tahun untuk semua produk",
        "confidence": 0.85,
    },
    {
        "category": "contact",
        "patterns": [
            "hubungi cs bagaimana",
            "nomor whatsapp",
            "email support",
            "customer service",
            "kontak",
            "admin",
        ],
        "answer": "Hubungi kami:\n• WhatsApp: +62 812-3456-7890\n• Email: support@company.com\n• Jam operasional: 09.00-21.00 WIB",
        "confidence": 0.9,
    },
    {
        "category": "location",
        "patterns": [
            "lokasi toko dimana",
            "alamat toko",
            "cabang ada dimana",
            "store location",
            "alamat kantor",
        ],
        "answer": "Alamat kami:\nJl. Raya Utama No. 123\nJakarta Selatan, 12345\n\nGoogle Maps: bit.ly/company-location",
        "confidence": 0.85,
    },
    {
        "category": "pricing",
        "patterns": [
            "harga berapa",
            "ada diskon",
            "promo bulan ini",
            "katalog harga",
            "daftar harga",
        ],
        "answer": "Untuk info harga dan katalog lengkap, silakan kunjungi:\n• Website: www.company.com\n• Marketplace: Tokopedia/Shopee (search: Company Official)\n\nPromo update setiap hari!",
        "confidence": 0.8,
    },
    {
        "category": "stock",
        "patterns": [
            "stok ada",
            "ready barang",
            "preorder berapa lama",
            "habis kapan restock",
            "tersedia",
        ],
        "answer": "Stok selalu update real-time di website. Jika tertera 'Ready', barang tersedia dan bisa langsung dikirim. Untuk PO, estimasi 7-14 hari.",
        "confidence": 0.85,
    },
]


async def seed_faqs():
    """Seed FAQs for all tenants."""
    
    print("\n" + "=" * 70)
    print("SEED FAQS - Default FAQ Database")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # Get all tenants
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        
        if not tenants:
            print("\n❌ No tenants found!")
            return
        
        print(f"\nFound {len(tenants)} tenant(s)")
        
        for tenant in tenants:
            print(f"\nSeeding FAQs for: {tenant.name} ({tenant.id})")
            
            # Check existing FAQs
            existing_result = await db.execute(
                select(TenantFAQ).where(TenantFAQ.tenant_id == tenant.id)
            )
            existing_faqs = existing_result.scalars().all()
            
            if existing_faqs:
                print(f"   Found {len(existing_faqs)} existing FAQs")
                
                # Skip seeding for this tenant if already has FAQs
                print(f"   Skipping (already has FAQs)")
                continue
            
            # Add default FAQs
            count = 0
            for faq_data in DEFAULT_FAQS:
                # Check if FAQ with this category already exists
                existing = await db.execute(
                    select(TenantFAQ).where(
                        TenantFAQ.tenant_id == tenant.id,
                        TenantFAQ.category == faq_data["category"]
                    )
                )
                if existing.scalar_one_or_none():
                    print(f"   Skipping {faq_data['category']} (already exists)")
                    continue
                
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
        
        print("\n" + "=" * 70)
        print("FAQ SEEDING COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    # Auto-run without prompt
    asyncio.run(seed_faqs())
