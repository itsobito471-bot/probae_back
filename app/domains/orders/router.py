from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date

from app.core.database import get_db
from .models import Order, OrderItem, OrderSource, OrderStatus
from .schemas import OrderListResponse, OrderPreviewRequest, OrderCheckoutRequest
from .scaling_service import scale_bowl
from app.domains.customers.models import Customer
from app.domains.bowls.models import Bowl, BowlIngredient

router = APIRouter(tags=["Orders"])

@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    source: Optional[OrderSource] = None,
    target_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Order)
    
    if source:
        query = query.where(Order.order_source == source)
    if target_date:
        query = query.where(Order.target_date == target_date)
        
    total_count = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    query = query.order_by(Order.target_date.desc(), Order.id.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    query = query.options(
        selectinload(Order.customer),
        selectinload(Order.items).selectinload(OrderItem.bowl)
    )
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    formatted_orders = []
    for o in orders:
        items = []
        for i in o.items:
            items.append({
                "id": i.id,
                "ulid": i.ulid,
                "bowl_id": i.bowl_id,
                "bowl_name": i.bowl.name if i.bowl else "Unknown",
                "meal_slot": i.meal_slot,
                "quantity": i.quantity,
                "adjusted_calories": i.adjusted_calories,
                "adjusted_macros": i.adjusted_macros,
                "adjusted_price": i.adjusted_price,
                "adjusted_ingredients": i.adjusted_ingredients
            })
            
        formatted_orders.append({
            "id": o.id,
            "ulid": o.ulid,
            "customer_id": o.customer_id,
            "plan_id": o.plan_id,
            "order_source": o.order_source,
            "status": o.status,
            "target_date": o.target_date,
            "total_order_price": o.total_order_price,
            "items": items,
            "customer": {"ulid": o.customer.ulid, "name": o.customer.name} if o.customer else None
        })
        
    return {
        "success": True,
        "orders": formatted_orders,
        "total_count": total_count,
        "page": page,
        "limit": limit
    }

@router.post("/preview")
async def preview_order(req: OrderPreviewRequest, db: AsyncSession = Depends(get_db)):
    customer = await db.scalar(select(Customer).where(Customer.ulid == req.customer_ulid))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    bowl = await db.scalar(
        select(Bowl)
        .where(Bowl.ulid == req.bowl_ulid)
        .options(selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient))
    )
    if not bowl:
        raise HTTPException(status_code=404, detail="Bowl not found")
        
    # Extract target calories for the requested slot
    calorie_profile = customer.calorie_profile or {}
    meal_calories = calorie_profile.get("mealCalories", {})
    target_cals = float(meal_calories.get(req.meal_slot, 0.0))
    goal = customer.goal or "MAINTENANCE"
    
    if target_cals <= 0:
        raise HTTPException(status_code=400, detail=f"Customer has no target calories for slot: {req.meal_slot}")
        
    scaled_result = await scale_bowl(bowl, target_cals, goal)
    
    return {
        "success": True,
        "preview": scaled_result.dict()
    }

@router.post("/checkout")
async def checkout_order(req: OrderCheckoutRequest, db: AsyncSession = Depends(get_db)):
    customer = await db.scalar(select(Customer).where(Customer.ulid == req.customer_ulid))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    total_price = 0.0
    new_order_items = []
    
    for item_data in req.items:
        bowl = await db.scalar(select(Bowl).where(Bowl.ulid == item_data.bowl_ulid))
        if not bowl:
            raise HTTPException(status_code=404, detail=f"Bowl {item_data.bowl_ulid} not found")
            
        new_item = OrderItem(
            bowl_id=bowl.id,
            meal_slot=item_data.meal_slot,
            quantity=item_data.quantity,
            adjusted_calories=item_data.adjusted_calories,
            adjusted_macros={
                "protein": item_data.adjusted_protein,
                "carbs": item_data.adjusted_carbs,
                "fat": item_data.adjusted_fat,
                "fiber": item_data.adjusted_fiber
            },
            adjusted_price=item_data.adjusted_price,
            adjusted_ingredients=[ing.dict() for ing in item_data.adjusted_ingredients]
        )
        new_order_items.append(new_item)
        total_price += item_data.adjusted_price * item_data.quantity
        
    new_order = Order(
        customer_id=customer.id,
        plan_id=None,
        order_source=OrderSource.CUSTOM,
        status=OrderStatus.CREATED,
        target_date=req.target_date,
        total_order_price=total_price
    )
    
    new_order.items = new_order_items
    db.add(new_order)
    await db.commit()
    
    return {"success": True, "order_ulid": new_order.ulid}
