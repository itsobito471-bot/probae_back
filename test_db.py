import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT name, calorie_profile FROM customers WHERE ulid = '01M17EZ3KDQ8671SVTEP4HVG2H'"))
        row = res.fetchone()
        if row:
            print(f"Customer Name: {row[0]}")
            print(f"Calorie Profile: {row[1]}")
        else:
            print("Customer not found")

if __name__ == "__main__":
    asyncio.run(main())
