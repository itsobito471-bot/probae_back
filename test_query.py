import asyncio
from app.core.database import AsyncSessionLocal
from app.domains.raw_materials.router import get_low_stock_count
from app.domains.users.models import User

async def main():
    async with AsyncSessionLocal() as db:
        res = await get_low_stock_count(current_user=User(), db=db)
        print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
