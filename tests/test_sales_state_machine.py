"""Test sales conversation state machine."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from app.services.conversation_state_machine import ConversationState, ConversationStage, ConversationSlots
from app.services.slot_extractor import get_slot_extractor
from app.services.state_handlers import get_state_handler


async def test_sales_flow():
    """Test complete sales conversation flow."""
    
    print("\n" + "=" * 70)
    print("SALES CONVERSATION STATE MACHINE TEST")
    print("=" * 70)
    
    extractor = get_slot_extractor()
    handler = get_state_handler()
    
    # Simulate conversation
    state = ConversationState()
    
    # Test messages simulating a sales conversation
    conversation = [
        "Halo",
        "Cari skincare untuk wajah berminyak",
        "50ribuan aja",
        "Yang nomor 1 dong",
        "Mau pesan",
        "Nama saya Budi",
        "081234567890",
        "Jl. Sudirman No. 123, Jakarta",
    ]
    
    print("\n📋 Simulating Sales Conversation:\n")
    
    for i, message in enumerate(conversation, 1):
        print(f"\n[{i}] User: {message}")
        print(f"    State before: {state.stage.value}")
        
        # Extract slots
        state.slots = extractor.extract(message, state.slots)
        
        # Handle state
        response, new_state = handler.handle_state(state, message)
        state = new_state
        
        print(f"    State after: {state.stage.value}")
        print(f"    Slots: {state.slots.to_dict()}")
        print(f"    Bot: {response[:100]}...")
    
    print("\n" + "=" * 70)
    print("✅ CONVERSATION FLOW TEST COMPLETED")
    print("=" * 70)
    
    print("\n📊 Final State:")
    print(f"  Stage: {state.stage.value}")
    print(f"  Slots: {state.slots.to_dict()}")
    print("=" * 70)


def test_slot_extraction():
    """Test slot extraction from various messages."""
    
    print("\n" + "=" * 70)
    print("SLOT EXTRACTION TEST")
    print("=" * 70)
    
    extractor = get_slot_extractor()
    
    test_cases = [
        ("Cari skincare untuk wajah berminyak", ["product_type", "skin_type"]),
        ("Budget 100ribuan", ["budget_min", "budget_max"]),
        ("Ambil 3 pcs", ["quantity"]),
        ("Yang nomor 1 aja", ["selected_product_name"]),
    ]
    
    print()
    
    for message, expected_slots in test_cases:
        slots = extractor.extract(message, ConversationSlots())
        
        print(f"Message: '{message}'")
        print(f"  Extracted: {slots.to_dict()}")
        
        for slot in expected_slots:
            value = getattr(slots, slot, None)
            status = "✅" if value else "❌"
            print(f"  {status} {slot}: {value}")
        print()
    
    print("=" * 70)


if __name__ == "__main__":
    test_slot_extraction()
    asyncio.run(test_sales_flow())
