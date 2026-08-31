import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from app.core.database import engine, Base, AsyncSessionLocal

# Import ALL domain models so SQLAlchemy's mapper can resolve
# all string-based relationship references (e.g. relationship("Packaging"))
import app.domains.users.models
import app.domains.bowls.models
import app.domains.packaging.models
import app.domains.ingredients.models
import app.domains.raw_materials.models
import app.domains.customers.models
import app.domains.orders.models
import app.domains.plans.models
import app.domains.vendors.models
import app.domains.documents.models
import app.domains.audit.models

# Domain Seeder Imports
from app.domains.users.seed import seed_users
from app.domains.bowls.seed import seed_meal_categories
# from app.domains.inventory.seed import seed_inventory  <-- You will uncomment this later!

async def run_all_seeds():
    print("⚙️  Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created successfully.\n")

    print("🚀 Starting Master Data Seeding...\n")
    async with AsyncSessionLocal() as db:
        try:
            # 1. Run User Domain Seeds
            await seed_users(db)
            
            # 2. Run Meal Category Seeds
            await seed_meal_categories(db)
            
            # 2. Run Inventory Domain Seeds (Once we build it)
            # await seed_inventory(db)
            
            # Commit all domain changes simultaneously 
            await db.commit()
            print("\n🎉 All domain seeding completed successfully!")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error during master seeding: {e}")

    # Close the database connection pool
    await engine.dispose()

if __name__ == "__main__":
    # Execute the master script
    asyncio.run(run_all_seeds())