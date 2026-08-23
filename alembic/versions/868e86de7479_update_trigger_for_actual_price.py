"""update_trigger_for_actual_price

Revision ID: 868e86de7479
Revises: 1864bc25e11e
Create Date: 2026-08-23 21:02:58.824652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '868e86de7479'
down_revision: Union[str, Sequence[str], None] = '1864bc25e11e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing trigger and function
    op.execute("DROP TRIGGER IF EXISTS trigger_update_ingredient_on_raw_material_update ON raw_materials;")
    op.execute("DROP FUNCTION IF EXISTS update_ingredient_on_raw_material_update();")
    
    # Recreate the function with COALESCE(r.actual_price, r.standard_price, r.price)
    op.execute("""
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
                SUM(COALESCE(r.calories, 0) * (irm.weight_g_or_ml / 100.0)) AS total_calories,
                SUM(COALESCE(r.protein, 0) * (irm.weight_g_or_ml / 100.0)) AS total_protein,
                SUM(COALESCE(r.carbs, 0) * (irm.weight_g_or_ml / 100.0)) AS total_carbs,
                SUM(COALESCE(r.fat, 0) * (irm.weight_g_or_ml / 100.0)) AS total_fat,
                SUM(COALESCE(r.fiber, 0) * (irm.weight_g_or_ml / 100.0)) AS total_fiber
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
    """)

    # Recreate trigger with standard_price and actual_price
    op.execute("""
    CREATE TRIGGER trigger_update_ingredient_on_raw_material_update
    AFTER UPDATE OF price, standard_price, actual_price, calories, protein, carbs, fat, fiber ON raw_materials
    FOR EACH ROW
    EXECUTE FUNCTION update_ingredient_on_raw_material_update();
    """)


def downgrade() -> None:
    # In downgrade, revert back to just using `r.price` and trigger without standard_price/actual_price
    op.execute("DROP TRIGGER IF EXISTS trigger_update_ingredient_on_raw_material_update ON raw_materials;")
    op.execute("DROP FUNCTION IF EXISTS update_ingredient_on_raw_material_update();")
    
    op.execute("""
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
                SUM((r.price / CASE WHEN r.unit IN ('KG', 'L') THEN 1000.0 ELSE 1.0 END) * irm.weight_g_or_ml) AS total_price,
                SUM(COALESCE(r.calories, 0) * (irm.weight_g_or_ml / 100.0)) AS total_calories,
                SUM(COALESCE(r.protein, 0) * (irm.weight_g_or_ml / 100.0)) AS total_protein,
                SUM(COALESCE(r.carbs, 0) * (irm.weight_g_or_ml / 100.0)) AS total_carbs,
                SUM(COALESCE(r.fat, 0) * (irm.weight_g_or_ml / 100.0)) AS total_fat,
                SUM(COALESCE(r.fiber, 0) * (irm.weight_g_or_ml / 100.0)) AS total_fiber
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
    """)

    op.execute("""
    CREATE TRIGGER trigger_update_ingredient_on_raw_material_update
    AFTER UPDATE OF price, calories, protein, carbs, fat, fiber ON raw_materials
    FOR EACH ROW
    EXECUTE FUNCTION update_ingredient_on_raw_material_update();
    """)
