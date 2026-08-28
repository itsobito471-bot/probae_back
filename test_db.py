import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT DISTINCT meal_type_code FROM plan_tier_selections;"))
        for row in res:
            print(row[0])

asyncio.run(main())
