"""fix macro trigger to use base unit weight instead of 100

Revision ID: da1c41f61f94
Revises: 206d52a13fc1
Create Date: 2026-09-08 17:30:18.326115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da1c41f61f94'
down_revision: Union[str, Sequence[str], None] = '206d52a13fc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Update the ingredient macro trigger to use base_unit_weight (1000.0 or 1.0) instead of 100.0
    op.execute('''
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
                SUM(COALESCE(r.calories, 0) * (irm.weight_g_or_ml / CASE WHEN r.unit IN ('KG', 'L') THEN 1000.0 ELSE 1.0 END)) AS total_calories,
                SUM(COALESCE(r.protein, 0) * (irm.weight_g_or_ml / CASE WHEN r.unit IN ('KG', 'L') THEN 1000.0 ELSE 1.0 END)) AS total_protein,
                SUM(COALESCE(r.carbs, 0) * (irm.weight_g_or_ml / CASE WHEN r.unit IN ('KG', 'L') THEN 1000.0 ELSE 1.0 END)) AS total_carbs,
                SUM(COALESCE(r.fat, 0) * (irm.weight_g_or_ml / CASE WHEN r.unit IN ('KG', 'L') THEN 1000.0 ELSE 1.0 END)) AS total_fat,
                SUM(COALESCE(r.fiber, 0) * (irm.weight_g_or_ml / CASE WHEN r.unit IN ('KG', 'L') THEN 1000.0 ELSE 1.0 END)) AS total_fiber
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
    ''')

    """Upgrade schema."""
    pass


def downgrade() -> None:

    # Revert to old behavior
    op.execute('''
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
    ''')

    """Downgrade schema."""
    pass
