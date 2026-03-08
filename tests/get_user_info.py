import asyncio
import logging
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User

async def get_user_info():
    async with async_session_factory() as db:
        r = await db.execute(select(User))
        users = r.scalars().all()
        with open("user_debug.txt", "w") as f:
            for u in users:
                f.write(f"Email: {u.email} | Role: {u.role} | ID: {u.id}\n")

if __name__ == "__main__":
    asyncio.run(get_user_info())
