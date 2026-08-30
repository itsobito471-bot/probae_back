import asyncio
from app.core.database import AsyncSessionLocal
from app.domains.kds.router import get_prep_list
import datetime

async def main():
    async with AsyncSessionLocal() as db:
        res = await get_prep_list(datetime.date(2026, 8, 29), db)
        print(res)

if __name__ == "__main__":
    asyncio.run(main())
