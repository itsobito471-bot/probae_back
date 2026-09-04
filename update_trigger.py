import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def update_trigger():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text("""
        CREATE OR REPLACE FUNCTION update_ingredient_on_raw_material_update()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE ingredients i
            SET 
                total_weight = subquery.total_weight,
                total_price = subquery.total_price,
                total_calories = subquery.total_calories,
                total_protein = subquery.total_protein,
                total_carbs = subquery.total_carbs,
                total_fat = subquery.total_fat,
                total_fiber = subquery.total_fiber
            FROM (
                SELECT 
                    irm.ingredient_id,
                    SUM(irm.weight_g_or_ml) AS total_weight,
                    SUM((COALESCE(r.actual_price, r.standard_price, r.price) / CASE WHEN r.unit IN ('KG', 'L') THEN 1000.0 ELSE 1.0 END) * irm.weight_g_or_ml) AS total_price,
                    ROUND(SUM(COALESCE(r.calories, 0) * (irm.weight_g_or_ml / 100.0))) AS total_calories,
                    ROUND(SUM(COALESCE(r.protein, 0) * (irm.weight_g_or_ml / 100.0))) AS total_protein,
                    ROUND(SUM(COALESCE(r.carbs, 0) * (irm.weight_g_or_ml / 100.0))) AS total_carbs,
                    ROUND(SUM(COALESCE(r.fat, 0) * (irm.weight_g_or_ml / 100.0))) AS total_fat,
                    ROUND(SUM(COALESCE(r.fiber, 0) * (irm.weight_g_or_ml / 100.0))) AS total_fiber
                FROM ingredient_raw_materials irm
                JOIN raw_materials r ON r.id = irm.raw_material_id
                WHERE irm.ingredient_id IN (
                    SELECT ingredient_id FROM ingredient_raw_materials WHERE raw_material_id = NEW.id
                )
                GROUP BY irm.ingredient_id
            ) AS subquery
            WHERE i.id = subquery.ingredient_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """))
    print("Successfully updated database trigger to round macros!")
    
if __name__ == "__main__":
    asyncio.run(update_trigger())
