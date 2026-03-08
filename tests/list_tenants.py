import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.tenant import Tenant

async def list_tenants():
    async with async_session_factory() as db:
        r = await db.execute(select(Tenant).limit(10))
        tenants = r.scalars().all()
        for t in tenants:
            print(f"{t.id} - {t.name}")

if __name__ == "__main__":
    asyncio.run(list_tenants())
