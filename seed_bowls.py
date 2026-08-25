import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import generate_ulid
import random

async def run():
    engine = create_async_engine("postgresql+asyncpg://adilanwar:root@localhost:5432/probae")
    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO ingredients (ulid, code, name, description, total_weight, total_price, total_calories, total_protein, total_carbs, total_fat, total_fiber, created_at, updated_at)
            SELECT :ulid, :code, :name, 'Description', 100, 10, 50, 2, 10, 0.5, 3, NOW(), NOW()
            WHERE NOT EXISTS (SELECT 1 FROM ingredients WHERE name = CAST(:name AS VARCHAR))
        """), [
            {"ulid": generate_ulid(), "code": "ING-KALE", "name": "Kale"},
            {"ulid": generate_ulid(), "code": "ING-SPIN", "name": "Spinach"},
            {"ulid": generate_ulid(), "code": "ING-CARR", "name": "Carrots"},
            {"ulid": generate_ulid(), "code": "ING-QUINOA", "name": "Quinoa"},
            {"ulid": generate_ulid(), "code": "ING-CHIC", "name": "Grilled Chicken"},
            {"ulid": generate_ulid(), "code": "ING-BALS", "name": "Balsamic Dressing"}
        ])

        res = await conn.execute(text("SELECT id, name FROM ingredients LIMIT 6"))
        ing_map = {row[1]: row[0] for row in res.fetchall()}
        
        await conn.execute(text("""
            INSERT INTO bowl_categories (ulid, code, name, description, created_at, updated_at)
            SELECT :ulid, 'CAT-BLEND', 'Blends', 'Blend bowls', NOW(), NOW()
            WHERE NOT EXISTS (SELECT 1 FROM bowl_categories WHERE name = 'Blends')
        """), {"ulid": generate_ulid()})
        
        res = await conn.execute(text("SELECT id FROM bowl_categories WHERE name = 'Blends'"))
        bcat_id = res.scalar()

        bowls = [
            {"name": "Green Power Blend", "desc": "A healthy green blend.", "raw": 45.0, "fixed": 5.0, "total": 50.0},
            {"name": "Protein Packed Blend", "desc": "High protein blend.", "raw": 60.0, "fixed": 10.0, "total": 70.0},
            {"name": "Root Veggie Blend", "desc": "Earthy root veggies.", "raw": 35.0, "fixed": 5.0, "total": 40.0}
        ]

        for b in bowls:
            res = await conn.execute(text("SELECT id FROM bowls WHERE name = :name"), {"name": b["name"]})
            if not res.scalar():
                ulid = generate_ulid()
                await conn.execute(text("""
                    INSERT INTO bowls (ulid, code, name, description, bowl_type, status, raw_cost, fixed_cost, total_cost, category_id, created_at, updated_at)
                    VALUES (:ulid, :code, :name, :desc, 'BLEND', true, :raw, :fixed, :total, :cat_id, NOW(), NOW())
                """), {
                    "ulid": ulid,
                    "code": "BOWL-" + str(random.randint(1000, 9999)),
                    "name": b["name"],
                    "desc": b["desc"],
                    "raw": b["raw"],
                    "fixed": b["fixed"],
                    "total": b["total"],
                    "cat_id": bcat_id
                })
                
                res = await conn.execute(text("SELECT id FROM bowls WHERE name = :name"), {"name": b["name"]})
                bowl_id = res.scalar()
                
                if bowl_id and ing_map:
                    for name, i_id in ing_map.items():
                        if random.choice([True, False]):
                            await conn.execute(text("""
                                INSERT INTO bowl_ingredients (bowl_id, ingredient_id, section_name, weight_g_or_ml)
                                VALUES (:bid, :iid, CAST('BLENDS' AS bowlsection), :weight)
                            """), {"bid": bowl_id, "iid": i_id, "weight": random.randint(10, 50)})
        print("Done seeding blend bowls!")

asyncio.run(run())
