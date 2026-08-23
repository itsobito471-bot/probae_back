from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domains.bowls.models import MealCategory
from datetime import time

async def seed_meal_categories(db: AsyncSession):
    print("  -> Seeding Meal Categories...")
    
    default_categories = [
        {"slug": "breakfast", "name": "Breakfast", "color_code": "#ffd700", "time_from": time(6, 0), "time_to": time(11, 30)},
        {"slug": "lunch", "name": "Lunch", "color_code": "#4caf50", "time_from": time(12, 0), "time_to": time(16, 30)},
        {"slug": "dinner", "name": "Dinner", "color_code": "#6a0fad", "time_from": time(18, 0), "time_to": time(23, 0)},
        {"slug": "snack", "name": "Snack", "color_code": "#ff751f", "time_from": time(16, 30), "time_to": time(18, 0)},
        {"slug": "drinks", "name": "Drinks", "color_code": "#222222", "time_from": time(0, 0), "time_to": time(23, 59)},
    ]
    
    for cat_data in default_categories:
        result = await db.execute(select(MealCategory).filter(MealCategory.slug == cat_data["slug"]))
        existing_cat = result.scalar_one_or_none()
        
        if not existing_cat:
            new_cat = MealCategory(
                slug=cat_data["slug"],
                name=cat_data["name"],
                color_code=cat_data["color_code"],
                time_from=cat_data["time_from"],
                time_to=cat_data["time_to"]
            )
            db.add(new_cat)
        else:
            # Update existing records if already seeded
            existing_cat.color_code = cat_data["color_code"]
            existing_cat.time_from = cat_data["time_from"]
            existing_cat.time_to = cat_data["time_to"]
            
    await db.commit()
    print("  -> Meal Categories seeded successfully.")
