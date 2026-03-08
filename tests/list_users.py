import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User
from app.models.tenant import Tenant

async def list_users():
    async with async_session_factory() as db:
        r = await db.execute(select(User))
        users = r.scalars().all()
        for u in users:
            tr = await db.execute(select(Tenant).where(Tenant.id == u.tenant_id))
            tenant = tr.scalar_one_or_none()
            tenant_name = tenant.name if tenant else "Unknown"
            print(f"ID: {u.id} | Email: {u.email} | Role: {u.role} | Tenant: {tenant_name}")

if __name__ == "__main__":
    asyncio.run(list_users())
