import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User
from app.domains.bowls.models import Bowl, BowlIngredient, BowlCategory, MealCategory
from app.domains.ingredients.models import Ingredient
from app.domains.packaging.models import Packaging
from app.domains.bowls.schemas import BowlCreate, BowlUpdate, BowlResponse, PaginatedBowls

router = APIRouter()

@router.post("", response_model=BowlResponse, status_code=status.HTTP_201_CREATED)
async def create_bowl(
    payload: BowlCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.code:
        existing = await db.scalar(select(Bowl).where(Bowl.code == payload.code))
        if existing:
            raise HTTPException(status_code=400, detail="Bowl with this code already exists")
            
    existing_name = await db.scalar(select(Bowl).where(Bowl.name == payload.name))
    if existing_name:
        raise HTTPException(status_code=400, detail="Bowl with this name already exists")

    packaging_cost = 0.0
    pack_id = None
    if payload.packaging_ulid:
        pack = await db.scalar(select(Packaging).where(Packaging.ulid == payload.packaging_ulid))
        if not pack:
            raise HTTPException(status_code=404, detail="Packaging not found")
        pack_id = pack.id
        packaging_cost = float(pack.total_cost)

    new_bowl = Bowl(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        bowl_type=payload.bowl_type,
        status=payload.status,
        fixed_cost=payload.fixed_cost,
        category_id=payload.category_id,
        meal_category_id=payload.meal_category_id,
        packaging_id=pack_id,
        raw_cost=0.0,
        total_cost=0.0
    )
    db.add(new_bowl)
    await db.flush()

    raw_cost = 0.0
    for ing_input in payload.ingredients:
        ingredient = await db.scalar(select(Ingredient).where(Ingredient.ulid == ing_input.ingredient_ulid))
        if not ingredient:
            raise HTTPException(status_code=404, detail=f"Ingredient {ing_input.ingredient_ulid} not found")
        
        # Math: (Selected Weight / Base Recipe Weight) * Base Value
        base_weight = float(ingredient.total_weight)
        base_price = float(ingredient.total_price)
        
        if base_weight > 0:
            cost_contribution = (base_price / base_weight) * ing_input.weight_g_or_ml
            raw_cost += cost_contribution
            
        link = BowlIngredient(
            bowl_id=new_bowl.id,
            ingredient_id=ingredient.id,
            section_name=ing_input.section_name,
            weight_g_or_ml=ing_input.weight_g_or_ml
        )
        db.add(link)

    new_bowl.raw_cost = raw_cost
    new_bowl.total_cost = raw_cost + packaging_cost + float(payload.fixed_cost)
    
    await db.commit()
    
    result = await db.execute(
        select(Bowl)
        .options(selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient))
        .where(Bowl.id == new_bowl.id)
    )
    bowl = result.scalar_one()
    
    # Map ingredients to response format manually if needed, or let Pydantic handle it via aliases
    return bowl

@router.get("", response_model=PaginatedBowls)
async def list_bowls(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(Bowl)
    if search:
        query = query.where(Bowl.name.ilike(f"%{search}%"))
        
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(Bowl.id.desc()).offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    pages = math.ceil(total / page_size) if total else 0
    
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": pages}

@router.get("/{ulid}", response_model=BowlResponse)
async def get_bowl(ulid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Bowl)
        .options(selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient))
        .where(Bowl.ulid == ulid)
    )
    bowl = result.scalar_one_or_none()
    if not bowl:
        raise HTTPException(status_code=404, detail="Bowl not found")
        
    # Inject ingredient details for response mapping
    for link in bowl.ingredients:
        link.ingredient_ulid = link.ingredient.ulid
        link.ingredient_name = link.ingredient.name
        
    return bowl

@router.put("/{ulid}", response_model=BowlResponse)
async def update_bowl(
    ulid: str,
    payload: BowlUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Bowl)
        .options(selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient))
        .where(Bowl.ulid == ulid)
    )
    bowl = result.scalar_one_or_none()
    if not bowl:
        raise HTTPException(status_code=404, detail="Bowl not found")

    if payload.name is not None and payload.name != bowl.name:
        existing = await db.scalar(select(Bowl).where(Bowl.name == payload.name))
        if existing:
            raise HTTPException(status_code=400, detail="Bowl with this name already exists")
        bowl.name = payload.name
        
    if payload.code is not None:
        bowl.code = payload.code
    if payload.description is not None:
        bowl.description = payload.description
    if payload.bowl_type is not None:
        bowl.bowl_type = payload.bowl_type
    if payload.status is not None:
        bowl.status = payload.status
    if payload.fixed_cost is not None:
        bowl.fixed_cost = payload.fixed_cost
    if payload.category_id is not None:
        bowl.category_id = payload.category_id
    if payload.meal_category_id is not None:
        bowl.meal_category_id = payload.meal_category_id

    packaging_cost = 0.0
    if payload.packaging_ulid is not None:
        if payload.packaging_ulid == "":
            bowl.packaging_id = None
        else:
            pack = await db.scalar(select(Packaging).where(Packaging.ulid == payload.packaging_ulid))
            if not pack:
                raise HTTPException(status_code=404, detail="Packaging not found")
            bowl.packaging_id = pack.id
            packaging_cost = float(pack.total_cost)
    else:
        # keep existing packaging cost
        if bowl.packaging_id:
            pack = await db.get(Packaging, bowl.packaging_id)
            if pack:
                packaging_cost = float(pack.total_cost)

    if payload.ingredients is not None:
        await db.execute(BowlIngredient.__table__.delete().where(BowlIngredient.bowl_id == bowl.id))
        
        raw_cost = 0.0
        for ing_input in payload.ingredients:
            ingredient = await db.scalar(select(Ingredient).where(Ingredient.ulid == ing_input.ingredient_ulid))
            if not ingredient:
                raise HTTPException(status_code=404, detail=f"Ingredient {ing_input.ingredient_ulid} not found")
            
            base_weight = float(ingredient.total_weight)
            base_price = float(ingredient.total_price)
            
            if base_weight > 0:
                raw_cost += (base_price / base_weight) * ing_input.weight_g_or_ml
                
            link = BowlIngredient(
                bowl_id=bowl.id,
                ingredient_id=ingredient.id,
                section_name=ing_input.section_name,
                weight_g_or_ml=ing_input.weight_g_or_ml
            )
            db.add(link)
            
        bowl.raw_cost = raw_cost

    bowl.total_cost = float(bowl.raw_cost) + packaging_cost + float(bowl.fixed_cost)
    
    await db.commit()
    
    result = await db.execute(
        select(Bowl)
        .options(selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient))
        .where(Bowl.id == bowl.id)
    )
    updated_bowl = result.scalar_one()
    
    for link in updated_bowl.ingredients:
        link.ingredient_ulid = link.ingredient.ulid
        link.ingredient_name = link.ingredient.name
        
    return updated_bowl
