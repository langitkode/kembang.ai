import httpx
import asyncio
import json

async def test_omnichannel():
    print("Mulai pengujian Omnichannel Webhook...")
    async with httpx.AsyncClient(timeout=180.0) as client:
        # 1. Ensure user exists
        login_data = {"email": "test@kembang.ai", "password": "strongpassword123"}
        
        print("1. Registering/Logging in...")
        # Try register first
        await client.post(
            "http://127.0.0.1:8000/api/v1/auth/register", 
            json={**login_data, "tenant_name": "Test Agency"}
        )
        
        # Login
        res = await client.post("http://127.0.0.1:8000/api/v1/auth/login", json=login_data)
        if res.status_code != 200:
            print(f"Login failed: {res.text}")
            return
        token = res.json()["access_token"]
        
        # Get tenant info
        headers = {"Authorization": f"Bearer {token}"}
        res_user = await client.get("http://127.0.0.1:8000/api/v1/auth/me", headers=headers)
        
        user_data = res_user.json()
        print(f"DEBUG - /me response status: {res_user.status_code}")
        print(f"DEBUG - /me response body: {json.dumps(user_data, indent=2)}")
        
        if "tenant_id" not in user_data:
            print("ERROR: 'tenant_id' not found in response!")
            return

        tenant_id = user_data["tenant_id"]
        print(f"Menggunakan Tenant ID: {tenant_id}")

        # 2. Test WhatsApp Simulation
        print("\n--- 1. Testing WhatsApp Simulation ---")
        wa_payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "628123456789",
                            "text": {"body": "Halo, saya mau tanya tentang layanan chatbot ini."}
                        }]
                    }
                }]
            }]
        }
        res_wa = await client.post(
            f"http://127.0.0.1:8000/api/v1/omnichannel/{tenant_id}/whatsapp",
            json=wa_payload
        )
        print(f"Status WhatsApp: {res_wa.status_code}")
        print(f"Reply: {res_wa.json().get('reply')}")

        # 3. Test Telegram Simulation
        print("\n--- 2. Testing Telegram Simulation ---")
        tg_payload = {
            "message": {
                "from": {"id": 12345678},
                "text": "Bisa tolong jelaskan fitur auto-reply?"
            }
        }
        res_tg = await client.post(
            f"http://127.0.0.1:8000/api/v1/omnichannel/{tenant_id}/telegram",
            json=tg_payload
        )
        print(f"Status Telegram: {res_tg.status_code}")
        print(f"Reply: {res_tg.json().get('reply')}")

        # 4. Test Generic Fallback
        print("\n--- 3. Testing Generic Fallback ---")
        gen_payload = {
            "user_id": "custom-app-001",
            "message": "Cek ombak!"
        }
        res_gen = await client.post(
            f"http://127.0.0.1:8000/api/v1/omnichannel/{tenant_id}/generic",
            json=gen_payload
        )
        print(f"Status Generic: {res_gen.status_code}")
        print(f"Reply: {res_gen.json().get('reply')}")

if __name__ == "__main__":
    asyncio.run(test_omnichannel())
