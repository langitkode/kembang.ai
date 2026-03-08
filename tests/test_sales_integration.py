"""Integration test for sales chatbot with state machine."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.conversation import Conversation
from app.services.sales_rag_service import SalesRAGService


async def test_sales_integration():
    """Test sales conversation with real database."""
    
    print("\n" + "=" * 70)
    print("SALES CHATBOT INTEGRATION TEST")
    print("=" * 70)
    
    async with async_session_factory() as db:
        # Get tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("❌ No tenant found!")
            return
        
        print(f"\nUsing tenant: {tenant.name} ({tenant.id})")
        
        # Create sales RAG service
        sales_rag = SalesRAGService(db)
        
        # Simulate sales conversation
        conversation_flow = [
            "Halo",
            "Cari skincare untuk wajah berminyak",
            "Budget 100ribuan",
            "Yang pertama dong",
            "Mau pesan ah",
        ]
        
        print("\n📋 Simulating Sales Conversation:\n")
        
        conversation_id = None
        
        for i, message in enumerate(conversation_flow, 1):
            print(f"[{i}] User: {message}")
            
            result = await sales_rag.generate_response(
                tenant_id=tenant.id,
                conversation_id=conversation_id,
                user_identifier="test-user",
                user_message=message,
            )
            
            conversation_id = result["conversation_id"]
            
            print(f"    Intent: {result['intent']}")
            print(f"    State: {result.get('state', {}).get('stage', 'N/A')}")
            print(f"    Bot: {result['reply'][:150]}...")
            print()
        
        # Get conversation from DB
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = conv_result.scalar_one_or_none()
        
        if conv:
            print("=" * 70)
            print("💾 CONVERSATION SAVED TO DATABASE")
            print("=" * 70)
            print(f"Conversation ID: {conv.id}")
            print(f"State: {conv.state}")
            print("=" * 70)
        
        print("\n✅ INTEGRATION TEST COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_sales_integration())
