import asyncio
import uuid
from sqlalchemy import delete
from app.db.session import async_session_factory
from app.models.tenant import Tenant

async def test_delete(tenant_id_str):
    tenant_id = uuid.UUID(tenant_id_str)
    async with async_session_factory() as db:
        print(f"Deleting tenant {tenant_id} via explicit SQL DELETE...")
        try:
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
            print("Successfully deleted tenant via SQL.")
        except Exception as e:
            print(f"Error deleting tenant: {e}")
            await db.rollback()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(test_delete(sys.argv[1]))
    else:
        print("Usage: python test_delete.py <tenant_id>")
