"""Seed script for sample products."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from decimal import Decimal
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.product import Product


SAMPLE_PRODUCTS = [
    # Skincare - Oily Skin
    {
        "sku": "SKN-001",
        "name": "Oil-Control Serum",
        "description": "Serum ringan untuk kulit berminyak dengan niacinamide untuk mengontrol minyak dan memperkecil pori.",
        "category": "skincare",
        "subcategory": "serum",
        "price": Decimal("95000"),
        "stock_quantity": 50,
        "attributes": {
            "skin_type": ["berminyak", "kombinasi"],
            "benefits": ["oil-control", "pore-minimizer", "brightening"],
            "key_ingredients": ["Niacinamide", "Zinc PCA", "Hyaluronic Acid"],
        },
    },
    {
        "sku": "SKN-002",
        "name": "Acne Fighting Toner",
        "description": "Toner dengan salicylic acid untuk melawan jerawat dan mencegah breakout.",
        "category": "skincare",
        "subcategory": "toner",
        "price": Decimal("85000"),
        "discount_price": Decimal("75000"),
        "stock_quantity": 30,
        "attributes": {
            "skin_type": ["berminyak", "berjerawat"],
            "benefits": ["acne-fighting", "oil-control", "exfoliating"],
            "key_ingredients": ["Salicylic Acid", "Tea Tree", "Witch Hazel"],
        },
    },
    {
        "sku": "SKN-003",
        "name": "Lightweight Moisturizer",
        "description": "Pelembab gel yang ringan, tidak lengket, cocok untuk kulit berminyak.",
        "category": "skincare",
        "subcategory": "moisturizer",
        "price": Decimal("120000"),
        "stock_quantity": 40,
        "attributes": {
            "skin_type": ["berminyak", "normal", "kombinasi"],
            "benefits": ["hydrating", "oil-free", "non-comedogenic"],
            "key_ingredients": ["Hyaluronic Acid", "Aloe Vera", "Green Tea"],
        },
    },
    
    # Skincare - Dry Skin
    {
        "sku": "SKN-004",
        "name": "Deep Hydration Serum",
        "description": "Serum intensif untuk kulit kering dengan triple hyaluronic acid.",
        "category": "skincare",
        "subcategory": "serum",
        "price": Decimal("135000"),
        "stock_quantity": 25,
        "attributes": {
            "skin_type": ["kering", "dehidrasi"],
            "benefits": ["hydrating", "plumping", "barrier-repair"],
            "key_ingredients": ["Hyaluronic Acid", "Vitamin B5", "Ceramides"],
        },
    },
    {
        "sku": "SKN-005",
        "name": "Rich Night Cream",
        "description": "Krim malam yang kaya nutrisi untuk kulit kering dan matang.",
        "category": "skincare",
        "subcategory": "moisturizer",
        "price": Decimal("180000"),
        "stock_quantity": 20,
        "attributes": {
            "skin_type": ["kering", "matang"],
            "benefits": ["anti-aging", "nourishing", "firming"],
            "key_ingredients": ["Retinol", "Peptides", "Shea Butter"],
        },
    },
    
    # Skincare - Whitening
    {
        "sku": "SKN-006",
        "name": "Vitamin C Brightening Serum",
        "description": "Serum vitamin C 15% untuk mencerahkan dan meratakan warna kulit.",
        "category": "skincare",
        "subcategory": "serum",
        "price": Decimal("145000"),
        "discount_price": Decimal("125000"),
        "stock_quantity": 35,
        "attributes": {
            "skin_type": ["semua jenis kulit"],
            "benefits": ["brightening", "whitening", "antioxidant"],
            "key_ingredients": ["Vitamin C 15%", "Vitamin E", "Ferulic Acid"],
        },
    },
    
    # Makeup
    {
        "sku": "MKP-001",
        "name": "Long-Lasting Foundation",
        "description": "Foundation tahan air dengan coverage medium to full, tahan hingga 12 jam.",
        "category": "makeup",
        "subcategory": "foundation",
        "price": Decimal("165000"),
        "stock_quantity": 45,
        "attributes": {
            "finish": ["matte", "natural"],
            "coverage": ["medium", "full"],
            "benefits": ["long-lasting", "waterproof", "transfer-proof"],
        },
    },
    {
        "sku": "MKP-002",
        "name": "Matte Lipstick",
        "description": "Lipstik matte dengan formula ringan, tidak membuat bibir kering.",
        "category": "makeup",
        "subcategory": "lipstick",
        "price": Decimal("75000"),
        "stock_quantity": 60,
        "attributes": {
            "finish": ["matte"],
            "benefits": ["long-lasting", "lightweight", "pigmented"],
            "shades": ["Red Velvet", "Pink Blossom", "Nude Beige", "Berry Wine"],
        },
    },
    
    # Bodycare
    {
        "sku": "BDY-001",
        "name": "Whitening Body Lotion",
        "description": "Lotion tubuh dengan vitamin B3 dan SPF 30 untuk mencerahkan dan melindungi.",
        "category": "bodycare",
        "subcategory": "body lotion",
        "price": Decimal("55000"),
        "stock_quantity": 100,
        "attributes": {
            "benefits": ["whitening", "moisturizing", "sun-protection"],
            "spf": "30",
            "key_ingredients": ["Vitamin B3", "Vitamin E", "Sunscreen"],
        },
    },
    
    # Haircare
    {
        "sku": "HRC-001",
        "name": "Anti-Dandruff Shampoo",
        "description": "Sampo anti ketombe dengan zinc pyrithione untuk kulit kepala sehat.",
        "category": "haircare",
        "subcategory": "shampoo",
        "price": Decimal("48000"),
        "stock_quantity": 80,
        "attributes": {
            "benefits": ["anti-dandruff", "soothing", "cleansing"],
            "hair_type": ["all hair types", "oily scalp"],
            "key_ingredients": ["Zinc Pyrithione", "Menthol", "Aloe Vera"],
        },
    },
]


async def seed_products():
    """Seed products for all tenants."""
    
    print("\n" + "=" * 70)
    print("SEED PRODUCTS - Sample Product Catalog")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # Get all tenants
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        
        if not tenants:
            print("\n❌ No tenants found! Please create a tenant first.")
            return
        
        print(f"\nFound {len(tenants)} tenant(s)")
        
        for tenant in tenants:
            print(f"\n📦 Seeding products for: {tenant.name} ({tenant.id})")
            
            # Check if products already exist
            existing = await db.execute(
                select(Product).where(Product.tenant_id == tenant.id).limit(1)
            )
            if existing.scalar_one_or_none():
                print(f"   ℹ️  Products already exist, skipping...")
                continue
            
            # Add sample products
            count = 0
            for product_data in SAMPLE_PRODUCTS:
                product = Product(
                    tenant_id=tenant.id,
                    **product_data
                )
                db.add(product)
                count += 1
            
            await db.commit()
            print(f"   ✅ Added {count} products")
        
        print("\n" + "=" * 70)
        print("✅ PRODUCT SEEDING COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_products())
