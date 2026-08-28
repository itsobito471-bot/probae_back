from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.domains.plans.models import PlanTier, PlanTierSelection
from app.domains.bowls.models import Bowl
from app.domains.plans.schemas import PlanTierCreate, PlanTierUpdate, PlanTierResponse, PlanTierListResponse

router = APIRouter(tags=["Plan Tiers"])

@router.get("", response_model=PlanTierListResponse)
async def list_tiers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(PlanTier).where(PlanTier.is_deleted == False)
    
    if search:
        query = query.where(
            PlanTier.name.ilike(f"%{search}%") | PlanTier.category.ilike(f"%{search}%")
        )
        
    total_count = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    query = query.order_by(PlanTier.id.desc()).offset((page - 1) * limit).limit(limit)
    # Load selections and bowls for the list if needed, or omit for performance
    query = query.options(selectinload(PlanTier.selections).selectinload(PlanTierSelection.bowl))
    
    result = await db.execute(query)
    tiers = result.scalars().all()
    
    # Transform to response
    formatted_tiers = []
    for tier in tiers:
        # Group selections by type
        selections_dict = {}
        for sel in tier.selections:
            if sel.meal_type_code not in selections_dict:
                selections_dict[sel.meal_type_code] = []
            selections_dict[sel.meal_type_code].append((sel.day_index, sel.bowl))
            
        formatted_selections = []
        for m_type, items in selections_dict.items():
            items.sort(key=lambda x: x[0]) # sort by day_index
            bowls = [{"id": b.id, "ulid": b.ulid, "name": b.name, "total_cost": b.total_cost, "raw_cost": b.raw_cost} for _, b in items]
            formatted_selections.append({"type": m_type, "bowls": bowls})
            
        formatted_tiers.append({
            "id": tier.id,
            "ulid": tier.ulid,
            "name": tier.name,
            "category": tier.category,
            "duration": tier.duration,
            "days": tier.days,
            "mealType": tier.meal_type,
            "totalPrice": tier.total_price,
            "discountPrice": tier.discount_price,
            "selections": formatted_selections
        })

    return {
        "success": True,
        "tiers": formatted_tiers,
        "totalCount": total_count,
        "page": page,
        "limit": limit
    }

@router.post("")
async def create_tier(data: PlanTierCreate, db: AsyncSession = Depends(get_db)):
    new_tier = PlanTier(
        name=data.name,
        category=data.category,
        duration=data.duration,
        days=data.days,
        meal_type=data.mealType,
        total_price=data.totalPrice,
        discount_price=data.discountPrice or 0.0
    )
    db.add(new_tier)
    await db.flush()
    
    # Process selections
    for sel in data.selections:
        for day_idx, bowl_ulid in enumerate(sel.bowls):
            # Fetch bowl ID by ULID
            bowl = await db.scalar(select(Bowl).where(Bowl.ulid == bowl_ulid))
            if bowl:
                new_sel = PlanTierSelection(
                    plan_tier_id=new_tier.id,
                    meal_type_code=sel.type,
                    day_index=day_idx,
                    bowl_id=bowl.id
                )
                db.add(new_sel)
                
    await db.commit()
    return {"success": True, "ulid": new_tier.ulid}

@router.get("/{ulid}")
async def get_tier(ulid: str, db: AsyncSession = Depends(get_db)):
    tier = await db.scalar(
        select(PlanTier)
        .where(PlanTier.ulid == ulid, PlanTier.is_deleted == False)
        .options(selectinload(PlanTier.selections).selectinload(PlanTierSelection.bowl))
    )
    if not tier:
        raise HTTPException(status_code=404, detail="Plan Tier not found")
        
    selections_dict = {}
    for sel in tier.selections:
        if sel.meal_type_code not in selections_dict:
            selections_dict[sel.meal_type_code] = []
        selections_dict[sel.meal_type_code].append((sel.day_index, sel.bowl))
        
    formatted_selections = []
    for m_type, items in selections_dict.items():
        items.sort(key=lambda x: x[0])
        # We need imageId.url for the UI, let us return something mock or actual
        bowls = [{
            "_id": b.ulid, # Using _id to match UI expectations
            "name": b.name, 
            "basePrice": b.total_cost, 
            "baseCalories": b.raw_cost,
            "imageId": {"url": f"{b.image_filename}" if getattr(b, "image_filename", None) else None}
        } for _, b in items]
        formatted_selections.append({"type": m_type, "bowls": bowls})
        
    formatted_tier = {
        "_id": tier.ulid, # Frontend expects _id
        "name": tier.name,
        "category": tier.category,
        "duration": tier.duration,
        "days": tier.days,
        "mealType": tier.meal_type,
        "totalPrice": tier.total_price,
        "discountPrice": tier.discount_price,
        "selections": formatted_selections
    }
    return {"success": True, "tier": formatted_tier}

@router.patch("/{ulid}")
async def update_tier(ulid: str, data: PlanTierUpdate, db: AsyncSession = Depends(get_db)):
    tier = await db.scalar(select(PlanTier).where(PlanTier.ulid == ulid, PlanTier.is_deleted == False))
    if not tier:
        raise HTTPException(status_code=404, detail="Plan Tier not found")
        
    if data.name is not None: tier.name = data.name
    if data.category is not None: tier.category = data.category
    if data.duration is not None: tier.duration = data.duration
    if data.days is not None: tier.days = data.days
    if data.mealType is not None: tier.meal_type = data.mealType
    if data.totalPrice is not None: tier.total_price = data.totalPrice
    if data.discountPrice is not None: tier.discount_price = data.discountPrice
    
    if data.selections is not None:
        # Delete old selections
        await db.execute(PlanTierSelection.__table__.delete().where(PlanTierSelection.plan_tier_id == tier.id))
        
        # Add new selections
        for sel in data.selections:
            for day_idx, bowl_ulid in enumerate(sel.bowls):
                bowl = await db.scalar(select(Bowl).where(Bowl.ulid == bowl_ulid))
                if bowl:
                    new_sel = PlanTierSelection(
                        plan_tier_id=tier.id,
                        meal_type_code=sel.type,
                        day_index=day_idx,
                        bowl_id=bowl.id
                    )
                    db.add(new_sel)
                    
    await db.commit()
    return {"success": True}

@router.delete("/{ulid}")
async def delete_tier(ulid: str, db: AsyncSession = Depends(get_db)):
    tier = await db.scalar(select(PlanTier).where(PlanTier.ulid == ulid))
    if not tier:
        raise HTTPException(status_code=404, detail="Plan Tier not found")
    tier.is_deleted = True
    await db.commit()
    return {"success": True}

from app.domains.customers.models import Customer
from app.domains.orders.scaling_service import scale_bowl
from app.domains.plans.schemas import PlanPreviewRequest
from app.domains.bowls.models import BowlIngredient



from app.domains.customers.models import Customer
from app.domains.orders.scaling_service import scale_bowl
from app.domains.plans.schemas import PlanPreviewRequest
from app.domains.bowls.models import BowlIngredient

@router.post("/preview-customization")
async def preview_customization(req: PlanPreviewRequest, db: AsyncSession = Depends(get_db)):
    # 1. Fetch Goal and Meal Calories (Stateless or Stateful)
    goal = req.goal or "MAINTENANCE"
    meal_calories = req.meal_calories or {}

    if req.customer_ulid:
        customer = await db.scalar(select(Customer).where(Customer.ulid == req.customer_ulid))
        if customer:
            calorie_profile = customer.calorie_profile or {}
            meal_calories = calorie_profile.get("mealCalories", {})
            goal = customer.goal or "MAINTENANCE"

    # 2. Fetch PlanTier and Selections
    plan = await db.scalar(
        select(PlanTier)
        .where(PlanTier.ulid == req.plan_ulid, PlanTier.is_deleted == False)
        .options(
            selectinload(PlanTier.selections).selectinload(PlanTierSelection.bowl).selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient)
        )
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan Tier not found")

    # 3. Calculate Discount Percentage
    discount_pct = 0.0
    if plan.total_price and plan.total_price > 0 and plan.discount_price and plan.discount_price < plan.total_price:
        discount_pct = float((plan.total_price - plan.discount_price) / plan.total_price)

    gross_price = 0.0
    scaled_matrix = []

    # 4. Scale each bowl
    for sel in plan.selections:
                # Map short codes from PlanTierSelection to the frontend customer mealSlot keys
        code_map = {
            "B": "B-FAST",
            "L": "LUNCH",
            "D": "DINNER"
        }
        mapped_key = code_map.get(sel.meal_type_code, sel.meal_type_code)
        target_calories = float(meal_calories.get(mapped_key, 0.0))
        bowl = sel.bowl
        
        scaled_result = None
        if target_calories > 0 and bowl and bowl.ingredients:
            try:
                scaled_result = await scale_bowl(bowl, target_calories, goal)
                gross_price += scaled_result.final_price
            except Exception as e:
                print(f"Error scaling bowl {bowl.id}: {e}")
                gross_price += float(bowl.total_cost or 0)
        else:
            gross_price += float(bowl.total_cost or 0) if bowl else 0

        scaled_matrix.append({
            "meal_type": sel.meal_type_code,
            "day_index": sel.day_index,
            "bowl_ulid": bowl.ulid if bowl else None,
            "bowl_name": bowl.name if bowl else "Unknown",
            "target_calories": target_calories,
            "scaled_calories": scaled_result.total_calories if scaled_result else (bowl.raw_cost if bowl else 0),
            "scaled_protein": scaled_result.total_protein if scaled_result else 0,
            "scaled_carbs": scaled_result.total_carbs if scaled_result else 0,
            "scaled_fats": scaled_result.total_fat if scaled_result else 0,
            "scaled_price": scaled_result.final_price if scaled_result else (bowl.total_cost if bowl else 0),
        })

    discount_amount = gross_price * discount_pct
    final_discounted_price = gross_price - discount_amount

    return {
        "success": True,
        "gross_price": round(gross_price, 2),
        "discount_amount": round(discount_amount, 2),
        "discount_percentage": round(discount_pct * 100, 2),
        "final_discounted_price": round(final_discounted_price, 2),
        "scaled_matrix": scaled_matrix
    }

