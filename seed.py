import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from app.core.database import engine, Base, AsyncSessionLocal

# Domain Seeder Imports
from app.domains.users.seed import seed_users
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