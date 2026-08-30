from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import date
from typing import List, Dict, Any

from app.core.database import get_db
from app.domains.orders.models import Order, OrderItem, OrderStatus
from app.domains.ingredients.models import Ingredient, IngredientRawMaterial
from app.domains.raw_materials.models import RawMaterial
from app.domains.bowls.models import Bowl
from app.domains.packaging.models import Packaging

from .models import DailyPrepTask, PrepStatus
from .schemas import PrepListResponse, PrepComponent, PrepRawMaterial, PrepStatusUpdateRequest, AssemblyListResponse, AssemblyBowl, AssemblyComponent

router = APIRouter(prefix="/kds", tags=["Kitchen Display System"])

@router.get("/prep-list", response_model=PrepListResponse)
async def get_prep_list(target_date: date = Query(...), db: AsyncSession = Depends(get_db)):
    # 1. Fetch Order Items for the given date (exclude cancelled)
    items_query = (
        select(OrderItem)
        .join(Order)
        .where(
            Order.target_date == target_date,
            Order.status != OrderStatus.CANCELLED
        )
    )
    items_res = await db.scalars(items_query)
    order_items = items_res.all()

    total_bowls = 0
    # dict: ingredient_id -> { "name": str, "weight": float }
    component_totals: Dict[int, Dict[str, Any]] = {}

    for item in order_items:
        total_bowls += item.quantity
        
        # item.adjusted_ingredients is a list of dicts from the scaling engine
        # e.g. [{"ingredient_id": 1, "name": "...", "weight_g_or_ml": 150.0}, ...]
        for ing in item.adjusted_ingredients:
            ing_id = ing.get("ingredient_id")
            if not ing_id:
                # Fallback for legacy orders: ing.get("id") is BowlIngredient.id
                bi_id = ing.get("id")
                if bi_id:
                    # Resolve to Ingredient ID
                    from app.domains.bowls.models import BowlIngredient
                    
                    bi = await db.scalar(select(BowlIngredient).where(BowlIngredient.id == bi_id))
                    if bi:
                        ing_id = bi.ingredient_id
            
            if not ing_id:
                continue
                
            weight_val = ing.get("new_weight") if "new_weight" in ing else ing.get("weight_g_or_ml", 0.0)
            weight = float(weight_val) * item.quantity
            
            if ing_id not in component_totals:
                component_totals[ing_id] = {
                    "name": ing.get("name", "Unknown Component"),
                    "weight": 0.0
                }
            component_totals[ing_id]["weight"] += weight

    # 2. Fetch raw materials and total base weights for these ingredients
    ingredient_ids = list(component_totals.keys())
    
    # We need the Ingredient total_weight to compute proportions, and its raw materials
    # We can fetch them with selectinload
    ingredients_db = []
    if ingredient_ids:
        from sqlalchemy.orm import selectinload
        ing_query = (
            select(Ingredient)
            .where(Ingredient.id.in_(ingredient_ids))
            .options(
                selectinload(Ingredient.raw_materials).selectinload(IngredientRawMaterial.raw_material)
            )
        )
        ing_res = await db.scalars(ing_query)
        ingredients_db = ing_res.all()
        
    ing_map = {ing.id: ing for ing in ingredients_db}

    # 3. Fetch Prep Statuses for these ingredients on this date
    prep_tasks_query = (
        select(DailyPrepTask)
        .where(
            DailyPrepTask.target_date == target_date,
            DailyPrepTask.ingredient_id.in_(ingredient_ids) if ingredient_ids else False
        )
    )
    prep_tasks_res = await db.scalars(prep_tasks_query)
    prep_tasks_map = {pt.ingredient_id: pt.status for pt in prep_tasks_res.all()}

    # 4. Build response
    components_resp = []
    for ing_id, data in component_totals.items():
        total_needed = data["weight"]
        db_ing = ing_map.get(ing_id)
        
        raw_materials_resp = []
        if db_ing and db_ing.total_weight > 0:
            ratio = total_needed / float(db_ing.total_weight)
            for rm_link in db_ing.raw_materials:
                rm = rm_link.raw_material
                if rm:
                    rm_weight = float(rm_link.weight_g_or_ml) * ratio
                    raw_materials_resp.append(
                        PrepRawMaterial(
                            raw_material_id=rm.id,
                            name=rm.name,
                            total_weight_needed=round(rm_weight, 2)
                        )
                    )
        
        status = prep_tasks_map.get(ing_id, PrepStatus.UNCOOKED)
        
        components_resp.append(
            PrepComponent(
                ingredient_id=ing_id,
                name=data["name"],
                total_weight_needed=round(total_needed, 2),
                status=status,
                raw_materials=raw_materials_resp
            )
        )

    # Sort components by name
    components_resp.sort(key=lambda x: x.name)

    return PrepListResponse(
        target_date=target_date,
        total_bowls=total_bowls,
        components=components_resp
    )

@router.patch("/prep-list/{ingredient_id}/status")
async def update_prep_status(ingredient_id: int, req: PrepStatusUpdateRequest, target_date: date = Query(...), db: AsyncSession = Depends(get_db)):
    task = await db.scalar(
        select(DailyPrepTask)
        .where(
            DailyPrepTask.target_date == target_date,
            DailyPrepTask.ingredient_id == ingredient_id
        )
    )
    
    if task:
        task.status = req.status
    else:
        task = DailyPrepTask(
            target_date=target_date,
            ingredient_id=ingredient_id,
            status=req.status
        )
        db.add(task)
        
    await db.commit()
    return {"success": True, "status": task.status}


@router.get("/assembly-list", response_model=AssemblyListResponse)
async def get_assembly_list(target_date: date = Query(...), db: AsyncSession = Depends(get_db)):
    # 1. Fetch Order Items for the given date (exclude cancelled)
    from sqlalchemy.orm import selectinload
    items_query = (
        select(OrderItem)
        .join(Order)
        .where(
            Order.target_date == target_date,
            Order.status != OrderStatus.CANCELLED
        )
        .options(
            selectinload(OrderItem.bowl).selectinload(Bowl.packaging)
        )
    )
    items_res = await db.scalars(items_query)
    order_items = items_res.all()

    total_bowls = 0
    # bowl_id -> { "name", "packaging_name", "quantity", "components": { ingredient_id -> weight } }
    bowl_totals: Dict[int, Dict[str, Any]] = {}

    for item in order_items:
        total_bowls += item.quantity
        bowl_id = item.bowl_id
        
        if bowl_id not in bowl_totals:
            bowl_name = item.bowl.name if item.bowl else "Unknown Bowl"
            packaging_name = None
            if item.bowl and hasattr(item.bowl, 'packaging') and item.bowl.packaging:
                packaging_name = item.bowl.packaging.name
                
            bowl_totals[bowl_id] = {
                "name": bowl_name,
                "packaging_name": packaging_name,
                "quantity": 0,
                "components": {} # ing_id -> { name, weight }
            }
            
        bowl_totals[bowl_id]["quantity"] += item.quantity
        
        # Aggregate component weights for this bowl type
        for ing in item.adjusted_ingredients:
            ing_id = ing.get("ingredient_id")
            if not ing_id:
                # Fallback for legacy orders: ing.get("id") is BowlIngredient.id
                bi_id = ing.get("id")
                if bi_id:
                    # Resolve to Ingredient ID
                    from app.domains.bowls.models import BowlIngredient
                    
                    bi = await db.scalar(select(BowlIngredient).where(BowlIngredient.id == bi_id))
                    if bi:
                        ing_id = bi.ingredient_id
            
            if not ing_id:
                continue
                
            weight_val = ing.get("new_weight") if "new_weight" in ing else ing.get("weight_g_or_ml", 0.0)
            weight = float(weight_val) * item.quantity
            
            if ing_id not in bowl_totals[bowl_id]["components"]:
                bowl_totals[bowl_id]["components"][ing_id] = {
                    "name": ing.get("name", "Unknown"),
                    "weight": 0.0
                }
            bowl_totals[bowl_id]["components"][ing_id]["weight"] += weight

    # Build response
    bowls_resp = []
    for b_id, data in bowl_totals.items():
        comp_list = []
        for ing_id, comp_data in data["components"].items():
            comp_list.append(
                AssemblyComponent(
                    ingredient_id=ing_id,
                    name=comp_data["name"],
                    weight_needed=round(comp_data["weight"], 2)
                )
            )
        comp_list.sort(key=lambda x: x.name)
        
        bowls_resp.append(
            AssemblyBowl(
                bowl_id=b_id,
                bowl_name=data["name"],
                packaging_name=data["packaging_name"],
                quantity=data["quantity"],
                components=comp_list
            )
        )
        
    bowls_resp.sort(key=lambda x: x.bowl_name)

    return AssemblyListResponse(
        target_date=target_date,
        total_bowls=total_bowls,
        bowls=bowls_resp
    )
