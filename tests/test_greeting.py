"""Test dynamic greeting."""

import asyncio
import httpx


async def test_greeting():
    """Test if greeting is dynamic."""
    
    print("\n" + "=" * 70)
    print("DYNAMIC GREETING TEST")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        print("\n[1] Logging in...")
        login_res = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"email": "test@kembang.ai", "password": "test123"}
        )
        
        if login_res.status_code != 200:
            print(f"❌ Login failed: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("OK Login successful")
        
        # Send "Halo" to trigger INIT state
        print("\n[2] Sending 'Halo' to trigger greeting...")
        chat_res = await client.post(
            "http://localhost:8000/api/v1/chat/message",
            headers=headers,
            json={"message": "Halo", "user_identifier": "test-greeting"}
        )
        
        if chat_res.status_code != 200:
            print(f"❌ Chat failed: {chat_res.text}")
            return
        
        response = chat_res.json()
        print(f"\n    Reply: {response['reply']}")
        print(f"    Intent: {response.get('intent', 'N/A')}")
        
        # Check if greeting is dynamic
        reply_lower = response['reply'].lower()
        
        import datetime
        hour = datetime.datetime.now().hour
        
        expected_greetings = []
        if 5 <= hour < 12:
            expected_greetings = ["selamat pagi"]
        elif 12 <= hour < 15:
            expected_greetings = ["selamat siang"]
        elif 15 <= hour < 18:
            expected_greetings = ["selamat sore"]
        else:
            expected_greetings = ["selamat malam"]
        
        print(f"\n[3] Checking greeting...")
        print(f"    Current hour: {hour}")
        print(f"    Expected: {expected_greetings[0]}")
        
        has_dynamic = any(g in reply_lower for g in expected_greetings)
        
        if has_dynamic:
            print(f"    OK GREETING IS DYNAMIC!")
        else:
            print(f"    ERROR GREETING IS STILL HARDCODED")
            print(f"       Expected one of: {expected_greetings}")
            print(f"       Got: {reply_lower[:100]}")
        
        print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_greeting())
