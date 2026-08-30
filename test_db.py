import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import async_session_maker
from app.domains.ingredients.models import Ingredient

async def main():
    async with async_session_maker() as session:
        query = select(Ingredient).options(selectinload(Ingredient.raw_materials))
        result = await session.execute(query)
        items = result.scalars().all()
        print(items)

asyncio.run(main())
