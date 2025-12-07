import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.session import engine
from app.models.post import Base

async def init_db():
    async with engine.begin() as conn:
        # Drop all tables (be careful in prod!)
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
