import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal

# Import models
from app.domains.users.models import User
from app.domains.customers.models import Customer
from app.domains.bowls.models import Bowl, BowlIngredient
from app.domains.ingredients.models import Ingredient
from app.domains.orders.scaling_service import scale_bowl

async def main():
    async with AsyncSessionLocal() as db:
        customer = await db.scalar(select(Customer).where(Customer.name == "Adil Anwar"))
        
        bowl = await db.scalar(
            select(Bowl)
            .options(selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient))
            .limit(1)
        )
        
        target_cals = 668.0
        goal = customer.goal or "MAINTENANCE"
        
        scaled_result = await scale_bowl(bowl, target_cals, goal)
        print(f"Bowl: {bowl.name}")
        print(f"Target Calories: {target_cals}")
        print(f"Scaled Result: {scaled_result.dict()}")

if __name__ == "__main__":
    asyncio.run(main())
