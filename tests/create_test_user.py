"""Create test user for Test Tenant."""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password


async def create_test_user():
    """Create test user for Test Tenant."""
    
    print("\n" + "=" * 60)
    print("CREATE TEST USER FOR TEST TENANT")
    print("=" * 60)
    
    async with async_session_factory() as db:
        # Find Test Tenant
        result = await db.execute(
            select(Tenant).where(Tenant.name == "Test Tenant")
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("[ERROR] Test Tenant not found!")
            return False
        
        print(f"\n[OK] Found Test Tenant: {tenant.id}")
        
        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == "test@kembang.ai")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"[INFO] User test@kembang.ai already exists")
            # Update password
            existing_user.password_hash = hash_password("test123")
            existing_user.role = "admin"
            print("[OK] Password updated to: test123")
        else:
            # Create user
            user = User(
                tenant_id=tenant.id,
                email="test@kembang.ai",
                password_hash=hash_password("test123"),
                role="admin",
            )
            db.add(user)
            print("[OK] User created with password: test123")
        
        await db.commit()
        
        print("\n" + "=" * 60)
        print("USER CREATED/UPDATED")
        print("=" * 60)
        print("\nLogin credentials:")
        print("  Email: test@kembang.ai")
        print("  Password: test123")
        print(f"  Tenant: {tenant.name}")
        
        return True


if __name__ == "__main__":
    asyncio.run(create_test_user())
