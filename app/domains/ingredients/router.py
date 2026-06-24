import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User
from app.domains.raw_materials.models import RawMaterial, UnitType
from .models import Ingredient, IngredientRawMaterial
from .schemas import IngredientCreate, IngredientUpdate, IngredientResponse, PaginatedIngredientResponse

router = APIRouter()

def get_base_unit_weight(unit: UnitType) -> float:
    if unit in (UnitType.KG, UnitType.L):
        return 1000.0
    return 1.0

@router.post("/", response_model=IngredientResponse, status_code=201)
async def create_ingredient(
    payload: IngredientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check uniqueness
    if payload.code:
        existing_code = await db.scalar(select(Ingredient).where(Ingredient.code == payload.code))
        if existing_code:
            raise HTTPException(status_code=400, detail="Ingredient with this code already exists.")
            
    existing_name = await db.scalar(select(Ingredient).where(Ingredient.name == payload.name))
    if existing_name:
        raise HTTPException(status_code=400, detail="Ingredient with this name already exists.")

    new_ingredient = Ingredient(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        image_filename=payload.image_filename,
        background_image_filename=payload.background_image_filename,
        created_by_id=current_user.id,
        total_weight=0,
        total_price=0,
        total_calories=0,
        total_protein=0,
        total_carbs=0,
        total_fat=0,
        total_fiber=0,
    )
    db.add(new_ingredient)
    await db.flush()  # To get new_ingredient.id

    for rm_input in payload.raw_materials:
        raw = await db.get(RawMaterial, rm_input.raw_material_id)
        if not raw:
            raise HTTPException(status_code=404, detail=f"Raw material with ID {rm_input.raw_material_id} not found.")

        # Math
        fraction = rm_input.weight_g_or_ml / 100.0
        base_unit_weight = get_base_unit_weight(raw.unit)
        price_contribution = (float(raw.price) / base_unit_weight) * rm_input.weight_g_or_ml

        new_ingredient.total_weight += rm_input.weight_g_or_ml
        new_ingredient.total_price += price_contribution
        new_ingredient.total_calories += float(raw.calories or 0) * fraction
        new_ingredient.total_protein += float(raw.protein or 0) * fraction
        new_ingredient.total_carbs += float(raw.carbs or 0) * fraction
        new_ingredient.total_fat += float(raw.fat or 0) * fraction
        new_ingredient.total_fiber += float(raw.fiber or 0) * fraction

        junction = IngredientRawMaterial(
            ingredient_id=new_ingredient.id,
            raw_material_id=raw.id,
            weight_g_or_ml=rm_input.weight_g_or_ml
        )
        db.add(junction)

    await db.commit()
    # Refetch with relationships
    result = await db.execute(
        select(Ingredient)
        .options(selectinload(Ingredient.raw_materials))
        .where(Ingredient.id == new_ingredient.id)
    )
    return result.scalar_one()

@router.get("/", response_model=PaginatedIngredientResponse)
async def list_ingredients(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Ingredient)
    
    if search:
        query = query.where(
            or_(
                Ingredient.name.ilike(f"%{search}%"),
                Ingredient.code.ilike(f"%{search}%")
            )
        )
        
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.order_by(Ingredient.id.desc()).offset((page - 1) * page_size).limit(page_size)
    query = query.options(selectinload(Ingredient.raw_materials))
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    pages = math.ceil(total / page_size) if total else 0
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }

@router.get("/{ulid}", response_model=IngredientResponse)
async def get_ingredient(
    ulid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Ingredient)
        .options(selectinload(Ingredient.raw_materials))
        .where(Ingredient.ulid == ulid)
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient

@router.put("/{ulid}", response_model=IngredientResponse)
async def update_ingredient(
    ulid: str,
    payload: IngredientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Ingredient)
        .options(selectinload(Ingredient.raw_materials))
        .where(Ingredient.ulid == ulid)
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    if payload.code is not None and payload.code != ingredient.code:
        existing_code = await db.scalar(select(Ingredient).where(Ingredient.code == payload.code))
        if existing_code:
            raise HTTPException(status_code=400, detail="Ingredient with this code already exists.")
            
    if payload.name is not None and payload.name != ingredient.name:
        existing_name = await db.scalar(select(Ingredient).where(Ingredient.name == payload.name))
        if existing_name:
            raise HTTPException(status_code=400, detail="Ingredient with this name already exists.")

    if payload.code is not None:
        ingredient.code = payload.code
    if payload.name is not None:
        ingredient.name = payload.name
    if payload.description is not None:
        ingredient.description = payload.description
    if payload.image_filename is not None:
        ingredient.image_filename = payload.image_filename
    if payload.background_image_filename is not None:
        ingredient.background_image_filename = payload.background_image_filename

    # If raw_materials are provided, recalculate everything
    if payload.raw_materials is str or payload.raw_materials is not None:
        # Delete existing
        await db.execute(
            IngredientRawMaterial.__table__.delete().where(IngredientRawMaterial.ingredient_id == ingredient.id)
        )
        
        ingredient.total_weight = 0
        ingredient.total_price = 0
        ingredient.total_calories = 0
        ingredient.total_protein = 0
        ingredient.total_carbs = 0
        ingredient.total_fat = 0
        ingredient.total_fiber = 0

        for rm_input in payload.raw_materials:
            raw = await db.get(RawMaterial, rm_input.raw_material_id)
            if not raw:
                raise HTTPException(status_code=404, detail=f"Raw material with ID {rm_input.raw_material_id} not found.")

            fraction = rm_input.weight_g_or_ml / 100.0
            base_unit_weight = get_base_unit_weight(raw.unit)
            price_contribution = (float(raw.price) / base_unit_weight) * rm_input.weight_g_or_ml

            ingredient.total_weight += rm_input.weight_g_or_ml
            ingredient.total_price += price_contribution
            ingredient.total_calories += float(raw.calories or 0) * fraction
            ingredient.total_protein += float(raw.protein or 0) * fraction
            ingredient.total_carbs += float(raw.carbs or 0) * fraction
            ingredient.total_fat += float(raw.fat or 0) * fraction
            ingredient.total_fiber += float(raw.fiber or 0) * fraction

            junction = IngredientRawMaterial(
                ingredient_id=ingredient.id,
                raw_material_id=raw.id,
                weight_g_or_ml=rm_input.weight_g_or_ml
            )
            db.add(junction)

    await db.commit()
    
    # Refetch to get updated relations
    result = await db.execute(
        select(Ingredient)
        .options(selectinload(Ingredient.raw_materials))
        .where(Ingredient.id == ingredient.id)
    )
    return result.scalar_one()

@router.delete("/{ulid}", status_code=204)
async def delete_ingredient(
    ulid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Ingredient).where(Ingredient.ulid == ulid))
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
        
    await db.delete(ingredient)
    await db.commit()
