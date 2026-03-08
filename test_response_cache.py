"""Test response cache functionality."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.services.response_cache import get_response_cache


async def test_cache():
    """Test response cache hit/miss."""
    
    print("\n" + "=" * 70)
    print("RESPONSE CACHE TEST")
    print("=" * 70)
    
    cache = get_response_cache()
    
    tenant_id = "test-tenant-001"
    
    # Test 1: Cache miss
    print("\n[Test 1] First query (should be MISS)...")
    result = cache.get(tenant_id, "Jam buka berapa?")
    print(f"    Result: {result}")
    print(f"    Stats: {cache.get_stats()}")
    
    # Test 2: Cache the response
    print("\n[Test 2] Caching response...")
    cache.set(
        tenant_id,
        "Jam buka berapa?",
        {"reply": "Kami buka setiap hari pukul 09.00-21.00 WIB.", "sources": []}
    )
    print(f"    Stats: {cache.get_stats()}")
    
    # Test 3: Cache hit
    print("\n[Test 3] Same query again (should be HIT)...")
    result = cache.get(tenant_id, "Jam buka berapa?")
    print(f"    Result: {result}")
    print(f"    Stats: {cache.get_stats()}")
    
    # Test 4: Different query (should be MISS)
    print("\n[Test 4] Different query (should be MISS)...")
    result = cache.get(tenant_id, "Harga berapa?")
    print(f"    Result: {result}")
    print(f"    Stats: {cache.get_stats()}")
    
    # Test 5: Case insensitive
    print("\n[Test 5] Same query, different case...")
    result = cache.get(tenant_id, "JAM BUKA BERAPA?")
    print(f"    Result: {result}")
    print(f"    Should be HIT (case-insensitive)")
    print(f"    Stats: {cache.get_stats()}")
    
    # Summary
    print("\n" + "=" * 70)
    print("CACHE STATISTICS")
    print("=" * 70)
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"    {key}: {value}")
    print("=" * 70)
    
    # Clear cache
    print("\n[Test 6] Clearing cache...")
    cache.clear()
    print(f"    Stats after clear: {cache.get_stats()}")
    
    print("\n✅ ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_cache())
