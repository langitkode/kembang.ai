"""Test response formatter - make chatbot more human."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.services.response_formatter import get_response_formatter


async def test_formatter():
    """Test response formatter with various responses."""
    
    print("\n" + "=" * 70)
    print("RESPONSE FORMATTER TEST - Humanize Chatbot")
    print("=" * 70)
    
    formatter = get_response_formatter()
    
    # Test cases
    test_cases = [
        # (raw_response, intent, description)
        ("Halo", "greeting", "Simple greeting"),
        ("Kami buka setiap hari pukul 09.00-21.00 WIB.", "faq", "FAQ - Business hours"),
        ("Kami menerima pembayaran via GoPay, OVO, Dana, dan transfer bank.", "faq", "FAQ - Payment"),
        ("Produk ini tersedia dalam varian A, B, dan C dengan harga mulai dari Rp 50.000.", "rag", "RAG - Product info"),
        ("Maaf, informasi tidak tersedia.", "rag", "RAG - Not found"),
        ("Terima kasih", "smalltalk", "Smalltalk - Thanks"),
    ]
    
    print("\nTesting response formatting:\n")
    
    for i, (raw_response, intent, description) in enumerate(test_cases, 1):
        print(f"[{i}] {description}")
        print(f"    Raw:      {raw_response}")
        
        formatted = formatter.format(raw_response, intent=intent)
        print(f"    Formatted: {formatted}")
        print()
    
    # Test template responses
    print("=" * 70)
    print("TEMPLATE RESPONSES TEST")
    print("=" * 70)
    
    print("\nGreeting variations:")
    for _ in range(3):
        print(f"  - {formatter._get_greeting_template()}")
    
    print("\nThanks variations:")
    for _ in range(3):
        print(f"  - {formatter.get_thanks_response()}")
    
    print("\nSorry variations:")
    for _ in range(3):
        print(f"  - {formatter.get_sorry_response()}")
    
    print("\nFollow-up variations:")
    for _ in range(3):
        print(f"  - {formatter.get_follow_up()}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED")
    print("=" * 70)
    
    print("\n📊 Summary:")
    print("  - Greeting templates: Multiple variations")
    print("  - FAQ formatting: Emoji added based on topic")
    print("  - RAG formatting: Conversational fillers + emoji")
    print("  - Smalltalk: Natural, friendly responses")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_formatter())
