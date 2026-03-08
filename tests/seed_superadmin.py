import asyncio
import uuid
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import select

async def create_superadmin(email: str, password: str):
    async with async_session_factory() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"User {email} already exists.")
            return

        # Create platform tenant if not exists
        result = await db.execute(select(Tenant).where(Tenant.name == "Kembang Platform"))
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name="Kembang Platform")
            db.add(tenant)
            await db.flush()
            print("Created platform tenant.")

        # Create superadmin user
        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(password),
            role="superadmin"
        )
        db.add(user)
        await db.commit()
        print(f"Successfully created superadmin user: {email}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python seed_superadmin.py <email> <password>")
    else:
        asyncio.run(create_superadmin(sys.argv[1], sys.argv[2]))
