import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.domains.customers.models import Customer
from app.domains.bowls.models import Bowl

async def main():
    async with AsyncSessionLocal() as db:
        # Find a customer with mealCalories
        customers = await db.scalars(select(Customer))
        cust = None
        for c in customers:
            if c.calorie_profile and c.calorie_profile.get("mealCalories"):
                cust = c
                break
        
        if not cust:
            print("No customer with mealCalories found")
            return
            
        print(f"Using Customer: {cust.name}, ULID: {cust.ulid}")
        print(f"Calorie Profile: {cust.calorie_profile}")
        
        # Pick any bowl
        bowl = await db.scalar(select(Bowl))
        print(f"Using Bowl: {bowl.name}, ULID: {bowl.ulid}")
        
        # Pick a meal slot from the customer's profile
        meal_slot = list(cust.calorie_profile["mealCalories"].keys())[0]
        print(f"Using Meal Slot: {meal_slot}")
        
        # Let's import the router directly or just print the logic
        target_cals = 0.0
        for k, v in cust.calorie_profile["mealCalories"].items():
            if k.lower() == meal_slot.lower():
                target_cals = float(v)
                break
        print(f"Extracted target_cals: {target_cals}")

if __name__ == "__main__":
    asyncio.run(main())
