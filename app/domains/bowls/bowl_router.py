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
    elif payload.packaging_id:
        pack = await db.get(Packaging, payload.packaging_id)
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
        image_filename=payload.image_filename,
        created_by_id=current_user.id,
        raw_cost=0.0,
        total_cost=0.0
    )
    db.add(new_bowl)
    await db.flush()

    raw_cost = 0.0
    for ing_input in payload.ingredients:
        ingredient = None
        if ing_input.ingredient_ulid:
            ingredient = await db.scalar(select(Ingredient).where(Ingredient.ulid == ing_input.ingredient_ulid))
        elif ing_input.ingredient_id:
            ingredient = await db.get(Ingredient, ing_input.ingredient_id)
            
        if not ingredient:
            ident = ing_input.ingredient_ulid or ing_input.ingredient_id
            raise HTTPException(status_code=404, detail=f"Ingredient {ident} not found")
        
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
        .options(
            selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient),
            selectinload(Bowl.meal_category),
            selectinload(Bowl.created_by)
        )
        .where(Bowl.id == new_bowl.id)
    )
    bowl = result.scalar_one()
    
    _inject_bowl_extras(bowl)

    return bowl

def _inject_bowl_extras(bowl: Bowl):
    total_cal = 0.0
    total_pro = 0.0
    total_carb = 0.0
    total_fat = 0.0
    total_fib = 0.0
    total_weight = 0.0
    for link in bowl.ingredients:
        link.ingredient_ulid = link.ingredient.ulid
        link.ingredient_name = link.ingredient.name
        
        base_weight = float(link.ingredient.total_weight)
        if base_weight > 0 and link.weight_g_or_ml > 0:
            ratio = float(link.weight_g_or_ml) / base_weight
            total_cal += float(link.ingredient.total_calories) * ratio
            total_pro += float(link.ingredient.total_protein) * ratio
            total_carb += float(link.ingredient.total_carbs) * ratio
            total_fat += float(link.ingredient.total_fat) * ratio
            total_fib += float(link.ingredient.total_fiber) * ratio
            total_weight += float(link.weight_g_or_ml)
            
    bowl.total_calories = round(total_cal, 2)
    bowl.total_protein = round(total_pro, 2)
    bowl.total_carbs = round(total_carb, 2)
    bowl.total_fat = round(total_fat, 2)
    bowl.total_fiber = round(total_fib, 2)
    bowl.total_weight = round(total_weight, 2)
    
    if bowl.created_by:
        bowl.created_by_name = f"{bowl.created_by.first_name} {bowl.created_by.last_name}".strip()
    else:
        bowl.created_by_name = "Admin"

@router.get("", response_model=PaginatedBowls)
async def list_bowls(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    count_q = select(func.count()).select_from(Bowl)
    query = select(Bowl).options(
        selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient),
        selectinload(Bowl.meal_category),
        selectinload(Bowl.created_by)
    )
    if search:
        query = query.where(Bowl.name.ilike(f"%{search}%"))
        count_q = count_q.where(Bowl.name.ilike(f"%{search}%"))
        
    total = await db.scalar(count_q)
    query = query.order_by(Bowl.id.desc()).offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    for bowl in items:
        _inject_bowl_extras(bowl)
    
    pages = math.ceil(total / page_size) if total else 0
    
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": pages}

@router.get("/{ulid}", response_model=BowlResponse)
async def get_bowl(ulid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Bowl)
        .options(
            selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient),
            selectinload(Bowl.meal_category),
            selectinload(Bowl.created_by)
        )
        .where(Bowl.ulid == ulid)
    )
    bowl = result.scalar_one_or_none()
    if not bowl:
        raise HTTPException(status_code=404, detail="Bowl not found")
        
    _inject_bowl_extras(bowl)
        
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
        .options(selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient), selectinload(Bowl.meal_category))
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
        
    provided_fields = payload.model_dump(exclude_unset=True)
    
    if "code" in provided_fields:
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
    if "meal_category_id" in provided_fields:
        bowl.meal_category_id = payload.meal_category_id
    if payload.image_filename is not None:
        bowl.image_filename = payload.image_filename

    packaging_cost = 0.0
    
    if "packaging_ulid" in provided_fields:
        if not payload.packaging_ulid:
            bowl.packaging_id = None
        else:
            pack = await db.scalar(select(Packaging).where(Packaging.ulid == payload.packaging_ulid))
            if not pack:
                raise HTTPException(status_code=404, detail="Packaging not found")
            bowl.packaging_id = pack.id
            packaging_cost = float(pack.total_cost)
    elif "packaging_id" in provided_fields:
        if not payload.packaging_id:
            bowl.packaging_id = None
        else:
            pack = await db.get(Packaging, payload.packaging_id)
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
            ingredient = None
            if ing_input.ingredient_ulid:
                ingredient = await db.scalar(select(Ingredient).where(Ingredient.ulid == ing_input.ingredient_ulid))
            elif ing_input.ingredient_id:
                ingredient = await db.get(Ingredient, ing_input.ingredient_id)
                
            if not ingredient:
                ident = ing_input.ingredient_ulid or ing_input.ingredient_id
                raise HTTPException(status_code=404, detail=f"Ingredient {ident} not found")
            
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
        .options(
            selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient),
            selectinload(Bowl.meal_category),
            selectinload(Bowl.created_by)
        )
        .where(Bowl.id == bowl.id)
    )
    updated_bowl = result.scalar_one()
    
    _inject_bowl_extras(updated_bowl)
        
    return updated_bowl
