import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User
from app.models.tenant import Tenant
from app.core.security import hash_password

async def reset_admin():
    email = "admin@kembang.ai"
    password = "password123"
    async with async_session_factory() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create platform tenant if not exists
            result = await db.execute(select(Tenant).where(Tenant.name == "Kembang Platform"))
            tenant = result.scalar_one_or_none()
            if not tenant:
                tenant = Tenant(name="Kembang Platform")
                db.add(tenant)
                await db.flush()
                print("Created platform tenant.")
            
            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=hash_password(password),
                role="superadmin"
            )
            db.add(user)
            print(f"Created new superadmin: {email}")
        else:
            user.password_hash = hash_password(password)
            user.role = "superadmin"
            print(f"Updated existing user {email} to superadmin and reset password.")
            
        await db.commit()
        print(f"Password for {email} has been set to {password}")

if __name__ == "__main__":
    asyncio.run(reset_admin())
