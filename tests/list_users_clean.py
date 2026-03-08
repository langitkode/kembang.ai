import asyncio
import logging
import os
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User
from app.models.tenant import Tenant

# Disable sqlalchemy logging for clean output
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

async def list_users():
    async with async_session_factory() as db:
        r = await db.execute(select(User))
        users = r.scalars().all()
        print("-" * 50)
        print(f"{'INDEX':<5} | {'EMAIL':<25} | {'ROLE':<10} | {'TENANT':<20}")
        print("-" * 50)
        for i, u in enumerate(users):
            tr = await db.execute(select(Tenant).where(Tenant.id == u.tenant_id))
            tenant = tr.scalar_one_or_none()
            tenant_name = tenant.name if tenant else "Unknown"
            print(f"{i:<5} | {u.email:<25} | {u.role:<10} | {tenant_name:<20}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(list_users())
