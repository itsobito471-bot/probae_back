import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.domains.orders.models import OrderItem
from app.domains.bowls.models import BowlIngredient

async def main():
    async with AsyncSessionLocal() as db:
        items = await db.scalars(select(OrderItem))
        count = 0
        for item in items:
            modified = False
            new_ingredients = []
            for ing in item.adjusted_ingredients:
                if "ingredient_id" not in ing:
                    # ing["id"] is BowlIngredient.id
                    bi_id = ing.get("id")
                    if bi_id:
                        bi = await db.scalar(select(BowlIngredient).where(BowlIngredient.id == bi_id))
                        if bi:
                            ing["ingredient_id"] = bi.ingredient_id
                            modified = True
                new_ingredients.append(ing)
            
            if modified:
                # Need to assign a new list to trigger SQLAlchemy JSON mutation detection (or use flag_modified)
                from sqlalchemy.orm.attributes import flag_modified
                item.adjusted_ingredients = new_ingredients
                flag_modified(item, "adjusted_ingredients")
                count += 1
                
        if count > 0:
            await db.commit()
            print(f"Fixed {count} order items in DB")
        else:
            print("No order items needed fixing")

if __name__ == "__main__":
    asyncio.run(main())
