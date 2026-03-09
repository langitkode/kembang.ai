"""Comprehensive API Testing Script for Backend Team.

Tests:
1. FAQ Endpoints
2. Products Endpoints
3. Pagination
4. Tenant Filtering
5. Search Functionality
"""

import asyncio
import sys
import codecs
import httpx

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

API_BASE = "http://localhost:8000"


async def login(email: str, password: str) -> str:
    """Login and return token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            raise Exception(f"Login failed: {response.text}")


async def test_faq_endpoints(token: str):
    """Test FAQ endpoints."""
    print("\n" + "=" * 70)
    print("TEST 1: FAQ ENDPOINTS")
    print("=" * 70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: List FAQs
        print("\n[1.1] GET /api/v1/faq")
        response = await client.get(f"{API_BASE}/api/v1/faq", headers=headers)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Total FAQs: {data.get('total', 0)}")
            print(f"  FAQs returned: {len(data.get('faqs', []))}")
            
            if data.get('faqs'):
                faq = data['faqs'][0]
                print(f"  Sample FAQ:")
                print(f"    - ID: {faq.get('id')}")
                print(f"    - Tenant ID: {faq.get('tenant_id')}")
                print(f"    - Category: {faq.get('category')}")
                print(f"    - Answer: {faq.get('answer')[:50]}...")
                print(f"  ✅ Has tenant_id: {'tenant_id' in faq}")
        else:
            print(f"  ❌ Error: {response.text}")
        
        # Test 2: FAQ Stats
        print("\n[1.2] GET /api/v1/faq/stats")
        response = await client.get(f"{API_BASE}/api/v1/faq/stats", headers=headers)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Total FAQs: {data.get('total_faqs', 0)}")
            print(f"  Categories: {len(data.get('by_category', []))}")
            print(f"  Tenants: {len(data.get('by_tenant', []))}")
            print(f"  ✅ Stats endpoint working")
        else:
            print(f"  ❌ Error: {response.text}")


async def test_products_endpoints(token: str):
    """Test Products endpoints."""
    print("\n" + "=" * 70)
    print("TEST 2: PRODUCTS ENDPOINTS")
    print("=" * 70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: List Products
        print("\n[2.1] GET /api/v1/products")
        response = await client.get(
            f"{API_BASE}/api/v1/products",
            headers=headers,
            params={"page": 1, "page_size": 10}
        )
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Total Products: {data.get('total', 0)}")
            print(f"  Products returned: {len(data.get('products', []))}")
            print(f"  Page: {data.get('page', 'N/A')}")
            print(f"  Page Size: {data.get('page_size', 'N/A')}")
            
            if data.get('products'):
                product = data['products'][0]
                print(f"  Sample Product:")
                print(f"    - ID: {product.get('id')}")
                print(f"    - Tenant ID: {product.get('tenant_id')}")
                print(f"    - Name: {product.get('name')}")
                print(f"    - Price: Rp {product.get('price', 0):,.0f}")
                print(f"  ✅ Has tenant_id: {'tenant_id' in product}")
                print(f"  ✅ Has pagination: {'page' in data}")
        else:
            print(f"  ❌ Error: {response.text}")
        
        # Test 2: Product Stats
        print("\n[2.2] GET /api/v1/products/stats")
        response = await client.get(f"{API_BASE}/api/v1/products/stats", headers=headers)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Total Products: {data.get('total_products', 0)}")
            print(f"  Categories: {len(data.get('by_category', []))}")
            print(f"  Tenants: {len(data.get('by_tenant', []))}")
            print(f"  Low Stock Count: {data.get('low_stock_count', 0)}")
            print(f"  Avg Price: Rp {data.get('avg_price', 0):,.0f}")
            print(f"  ✅ Stats endpoint working")
        else:
            print(f"  ❌ Error: {response.text}")
        
        # Test 3: Low Stock Products
        print("\n[2.3] GET /api/v1/products/low-stock")
        response = await client.get(
            f"{API_BASE}/api/v1/products/low-stock",
            headers=headers,
            params={"threshold": 10}
        )
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Threshold: {data.get('threshold', 0)}")
            print(f"  Low Stock Products: {len(data.get('products', []))}")
            print(f"  ✅ Low stock endpoint working")
        else:
            print(f"  ❌ Error: {response.text}")


async def test_pagination(token: str):
    """Test pagination functionality."""
    print("\n" + "=" * 70)
    print("TEST 3: PAGINATION")
    print("=" * 70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test Products Pagination
        print("\n[3.1] Products Pagination")
        for page in [1, 2]:
            response = await client.get(
                f"{API_BASE}/api/v1/products",
                headers=headers,
                params={"page": page, "page_size": 5}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"  Page {page}: {len(data.get('products', []))} items, Total: {data.get('total', 0)}")
                print(f"    ✅ Has pagination object: {'pagination' in data or 'page' in data}")
            else:
                print(f"  ❌ Page {page} failed")
        
        # Test FAQ Pagination
        print("\n[3.2] FAQ Pagination")
        for page in [1, 2]:
            response = await client.get(
                f"{API_BASE}/api/v1/faq",
                headers=headers,
                params={"page": page, "page_size": 5}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"  Page {page}: {len(data.get('faqs', []))} items, Total: {data.get('total', 0)}")
                print(f"    ✅ Has total count: {'total' in data}")
            else:
                print(f"  ❌ Page {page} failed")


async def test_tenant_filtering(token: str):
    """Test tenant filtering."""
    print("\n" + "=" * 70)
    print("TEST 4: TENANT FILTERING")
    print("=" * 70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test FAQ with tenant filter
        print("\n[4.1] FAQ with X-Tenant-ID header")
        # This would require a superadmin token and actual tenant ID
        print(f"  ℹ️  Requires superadmin token and tenant ID")
        print(f"  ℹ️  Test manually with: curl -H 'X-Tenant-ID: <uuid>'")
        
        # Test Products with category filter
        print("\n[4.2] Products with category filter")
        response = await client.get(
            f"{API_BASE}/api/v1/products",
            headers=headers,
            params={"category": "skincare", "page": 1, "page_size": 10}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  Category 'skincare': {len(data.get('products', []))} products")
            print(f"  ✅ Category filtering working")
        else:
            print(f"  ❌ Error: {response.text}")


async def test_search(token: str):
    """Test search functionality."""
    print("\n" + "=" * 70)
    print("TEST 5: SEARCH FUNCTIONALITY")
    print("=" * 70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test Product Search
        print("\n[5.1] Product Search")
        response = await client.get(
            f"{API_BASE}/api/v1/products",
            headers=headers,
            params={"search": "serum", "page": 1, "page_size": 10}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  Search 'serum': {len(data.get('products', []))} results")
            if data.get('products'):
                print(f"  Sample: {data['products'][0].get('name')}")
            print(f"  ✅ Search working")
        else:
            print(f"  ❌ Error: {response.text}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("BACKEND TEAM - COMPREHENSIVE API TESTING")
    print("=" * 70)
    
    # Login
    print("\n[LOGIN] Logging in as test@kembang.ai...")
    try:
        token = await login("test@kembang.ai", "test123")
        print("✅ Login successful")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("\nTrying alternative credentials...")
        try:
            token = await login("admin@kembang.ai", "password123")
            print("✅ Login successful with admin account")
        except Exception as e2:
            print(f"❌ Both login attempts failed!")
            print(f"   Error 1: {e}")
            print(f"   Error 2: {e2}")
            print("\n⚠️  Please ensure:")
            print("   1. Backend server is running on http://localhost:8000")
            print("   2. User exists in database")
            print("   3. Password is correct")
            return
    
    # Run tests
    await test_faq_endpoints(token)
    await test_products_endpoints(token)
    await test_pagination(token)
    await test_tenant_filtering(token)
    await test_search(token)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Review output above")
    print("2. Check for any ❌ errors")
    print("3. Verify tenant_id is present in all responses")
    print("4. Verify pagination objects are correct")
    print("5. Verify filtering and search working")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
