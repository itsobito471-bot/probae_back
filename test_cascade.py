import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.domains.raw_materials.models import RawMaterial
from app.domains.ingredients.models import Ingredient
from app.domains.bowls.models import Bowl

async def test():
    async with AsyncSessionLocal() as session:
        # Get raw material
        rm = await session.scalar(select(RawMaterial).limit(1))
        if not rm:
            print("No RM found")
            return
        
        print(f"Old standard price: {rm.standard_price}, actual: {rm.actual_price}")
        
        # update standard_price
        rm.standard_price = 999.0
        rm.actual_price = 1000.0
        await session.commit()
        
        print("Done update")

if __name__ == "__main__":
    asyncio.run(test())
