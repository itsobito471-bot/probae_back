import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal

# Import all models to avoid InvalidRequestError
from app.domains.users.models import User
from app.domains.documents.models import Document
from app.domains.settings.models import SystemSetting
from app.domains.raw_materials.models import RawMaterial
from app.domains.audit.models import AuditLog
from app.domains.ingredients.models import Ingredient, IngredientRawMaterial
from app.domains.bowls.models import BowlCategory, Bowl, BowlIngredient, MealCategory
from app.domains.packaging.models import Packaging, PackagingComponent, PackagingItemLink
from app.domains.vendors.models import Vendor
from app.domains.plans.models import PlanTier, PlanTierSelection
from app.domains.customers.models import Customer, CustomerCalorieLog
from app.domains.orders.models import Order, OrderItem

async def main():
    async with AsyncSessionLocal() as db:
        customers = await db.scalars(select(Customer))
        for c in customers:
            if c.calorie_profile and c.calorie_profile.get("mealCalories"):
                print(f"Customer: {c.name} | mealSlots: {c.calorie_profile.get('mealSlots')} | mealCalories: {c.calorie_profile.get('mealCalories')}")

if __name__ == "__main__":
    asyncio.run(main())
