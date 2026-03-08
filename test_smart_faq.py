"""Test smart FAQ matching dengan berbagai variasi query."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.services.intent_router import create_default_router


def test_smart_matching():
    """Test FAQ matching dengan berbagai variasi."""
    
    print("\n" + "=" * 70)
    print("SMART FAQ MATCHING TEST")
    print("=" * 70)
    
    router = create_default_router()
    
    # Test queries dengan berbagai variasi
    test_queries = [
        # Jam buka
        ("jam buka berapa", "Jam buka - exact"),
        ("buka jam berapa", "Jam buka - exact 2"),
        ("jam operasional", "Jam buka - synonym"),
        ("toko buka dari jam berapa", "Jam buka - longer"),
        ("bukanya jam berapa ya", "Jam buka - casual"),
        ("jam berapa buka", "Jam buka - reversed"),
        ("hari apa saja buka", "Jam buka - days"),
        
        # Payment
        ("bisa bayar pakai apa", "Payment - exact"),
        ("terima goPay", "Payment - ewallet"),
        ("transfer bca bisa", "Payment - bank"),
        ("ada cod", "Payment - cod"),
        ("bayar dimana", "Payment - where"),
        
        # Shipping
        ("ongkir berapa", "Shipping - exact"),
        ("berapa lama sampai", "Shipping - duration"),
        ("pakai ekspedisi apa", "Shipping - courier"),
        ("bisa kirim ke surabaya", "Shipping - location"),
        
        # Non-FAQ (should be RAG)
        ("produk apa yang bagus untuk wajah", "RAG - complex question"),
        ("saya punya masalah dengan pesanan", "RAG - complaint"),
    ]
    
    print(f"\nTesting {len(test_queries)} queries...\n")
    
    faq_count = 0
    rag_count = 0
    
    for query, description in test_queries:
        result = router.classify(query)
        
        intent = result.intent.value
        confidence = result.confidence
        has_answer = "Yes" if result.cached_answer else "No"
        
        if intent == "faq":
            faq_count += 1
            status = "✅ FAQ"
        else:
            rag_count += 1
            status = "🤖 RAG"
        
        print(f"{status} ({confidence:.0%}): {description}")
        print(f"       Query: '{query}'")
        if result.cached_answer:
            preview = result.cached_answer[:60].replace('\n', ' ')
            print(f"       Answer: {preview}...")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total queries: {len(test_queries)}")
    print(f"FAQ matches:   {faq_count} ({100*faq_count/len(test_queries):.0f}%)")
    print(f"RAG fallback:  {rag_count} ({100*rag_count/len(test_queries):.0f}%)")
    print("=" * 70)


if __name__ == "__main__":
    test_smart_matching()
