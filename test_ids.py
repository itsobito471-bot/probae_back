import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.domains.customers.models import Customer
from app.domains.bowls.models import Bowl

async def main():
    async with AsyncSessionLocal() as db:
        customer = await db.scalar(select(Customer))
        bowl = await db.scalar(select(Bowl))
        print(f"CUSTOMER_ULID={customer.ulid}")
        print(f"BOWL_ULID={bowl.ulid}")
        
if __name__ == "__main__":
    asyncio.run(main())
