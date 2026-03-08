"""Test Product CRUD API endpoints."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

import httpx


async def test_product_crud():
    """Test Product CRUD API."""
    
    API_BASE = "http://localhost:8000"
    
    print("\n" + "=" * 70)
    print("PRODUCT CRUD API TEST")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login
        print("\n[1] Logging in...")
        login_res = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": "test@kembang.ai", "password": "test123"}
        )
        
        if login_res.status_code != 200:
            print(f"❌ Login failed: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # 2. List existing products
        print("\n[2] Listing products...")
        products_res = await client.get(
            f"{API_BASE}/api/v1/products",
            headers=headers
        )
        
        if products_res.status_code == 200:
            products_data = products_res.json()
            print(f"✅ Found {products_data['total']} products")
            
            if products_data['products']:
                print(f"\n    First product:")
                first = products_data['products'][0]
                print(f"      Name: {first['name']}")
                print(f"      SKU: {first['sku']}")
                print(f"      Price: Rp {first['price']:,.0f}")
        else:
            print(f"❌ Failed: {products_res.text}")
        
        # 3. Get catalog metadata
        print("\n[3] Getting catalog metadata...")
        catalog_res = await client.get(
            f"{API_BASE}/api/v1/products/catalog/metadata",
            headers=headers
        )
        
        if catalog_res.status_code == 200:
            catalog_data = catalog_res.json()
            print(f"✅ Catalog metadata:")
            print(f"      Categories: {catalog_data['categories']}")
            print(f"      Skin types: {len(catalog_data['skin_types'])} types")
            print(f"      Concerns: {len(catalog_data['concerns'])} benefits")
            print(f"      Price range: Rp {catalog_data['price_range'][0]:,.0f} - {catalog_data['price_range'][1]:,.0f}")
        else:
            print(f"❌ Failed: {catalog_res.text}")
        
        # 4. Create a new product
        print("\n[4] Creating new product...")
        new_product = {
            "sku": f"TEST-{int(asyncio.get_event_loop().time())}",
            "name": "Test Product - Serum Whitening",
            "description": "Serum untuk mencerahkan kulit wajah",
            "category": "skincare",
            "subcategory": "serum",
            "price": 125000,
            "stock_quantity": 50,
            "is_active": True,
            "attributes": {
                "skin_type": ["berminyak", "kering"],
                "benefits": ["whitening", "brightening"],
                "key_ingredients": ["Vitamin C", "Niacinamide"]
            }
        }
        
        create_res = await client.post(
            f"{API_BASE}/api/v1/products",
            headers=headers,
            json=new_product
        )
        
        if create_res.status_code == 201:
            created = create_res.json()["product"]
            print(f"✅ Product created!")
            print(f"      ID: {created['id']}")
            print(f"      Name: {created['name']}")
            print(f"      Price: Rp {created['price']:,.0f}")
            
            # 5. Update the product
            print("\n[5] Updating product...")
            update_data = {
                "price": 99000,
                "discount_price": 75000
            }
            
            update_res = await client.put(
                f"{API_BASE}/api/v1/products/{created['id']}",
                headers=headers,
                json=update_data
            )
            
            if update_res.status_code == 200:
                updated = update_res.json()["product"]
                print(f"✅ Product updated!")
                print(f"      Original price: Rp {updated['price']:,.0f}")
                print(f"      Discount price: Rp {updated['discount_price']:,.0f}")
                print(f"      Final price: Rp {updated['final_price']:,.0f}")
            else:
                print(f"❌ Update failed: {update_res.text}")
            
            # 6. Get product detail
            print("\n[6] Getting product detail...")
            detail_res = await client.get(
                f"{API_BASE}/api/v1/products/{created['id']}",
                headers=headers
            )
            
            if detail_res.status_code == 200:
                detail = detail_res.json()["product"]
                print(f"✅ Product detail retrieved")
                print(f"      Attributes: {detail['attributes']}")
            else:
                print(f"❌ Failed: {detail_res.text}")
            
            # 7. Delete product (soft delete)
            print("\n[7] Deleting product...")
            delete_res = await client.delete(
                f"{API_BASE}/api/v1/products/{created['id']}",
                headers=headers
            )
            
            if delete_res.status_code == 204:
                print(f"✅ Product deleted (soft delete)")
            else:
                print(f"❌ Delete failed: {delete_res.text}")
        else:
            print(f"❌ Create failed: {create_res.text}")
        
        # 8. Test filters
        print("\n[8] Testing product filters...")
        
        # Filter by category
        filter_res = await client.get(
            f"{API_BASE}/api/v1/products?category=skincare&in_stock_only=true",
            headers=headers
        )
        
        if filter_res.status_code == 200:
            filtered = filter_res.json()
            print(f"✅ Filter by category (skincare): {filtered['total']} products")
        
        # Search
        search_res = await client.get(
            f"{API_BASE}/api/v1/products?search=serum",
            headers=headers
        )
        
        if search_res.status_code == 200:
            searched = search_res.json()
            print(f"✅ Search 'serum': {searched['total']} products")
        
        print("\n" + "=" * 70)
        print("✅ PRODUCT CRUD API TEST COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_product_crud())
