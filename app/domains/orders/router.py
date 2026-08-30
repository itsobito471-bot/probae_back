from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date

from app.core.database import get_db
from .models import Order, OrderItem, OrderSource, OrderStatus
from .schemas import OrderListResponse, OrderPreviewRequest, OrderCheckoutRequest, OrderStatusUpdateRequest, OrderSchema, OrderItemUpdateRequest
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
    search: Optional[str] = None,
    customer_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Order).join(Customer, Order.customer_id == Customer.id)
    
    if source:
        query = query.where(Order.order_source == source)
    if target_date:
        query = query.where(Order.target_date == target_date)
    if customer_id:
        query = query.where(Order.customer_id == customer_id)
    if status:
        query = query.where(Order.status == status)
    if search:
        search_str = f"%{search}%"
        or_conditions = [
            Customer.name.ilike(search_str),
            Customer.phone.ilike(search_str),
            Order.ulid.ilike(search_str)
        ]
        if search.isdigit():
            or_conditions.append(Order.id == int(search))
        query = query.where(or_(*or_conditions))
        
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
    # Map short codes from legacy DB to the frontend customer mealSlot keys
    code_map = {
        "B": "Breakfast",
        "L": "Lunch",
        "D": "Dinner",
        "S": "Snack",
        "B-FAST": "Breakfast",
        "BREAKFAST": "Breakfast",
        "LUNCH": "Lunch",
        "DINNER": "Dinner",
        "SNACK": "Snack"
    }
    
    req_mapped = code_map.get(req.meal_slot.upper(), req.meal_slot)
    
    target_cals = 0.0
    for k, v in meal_calories.items():
        k_mapped = code_map.get(k.upper(), k)
        if k.lower() == req.meal_slot.lower() or k_mapped.lower() == req_mapped.lower():
            target_cals = float(v)
            break
            
    goal = customer.goal or "MAINTENANCE"
    
    if target_cals <= 0:
        base_cals = 0.0
        for item in bowl.ingredients:
            if item.ingredient and item.ingredient.total_weight and item.ingredient.total_weight > 0:
                ratio = float(item.weight_g_or_ml) / float(item.ingredient.total_weight)
                base_cals += float(item.ingredient.total_calories) * ratio
        target_cals = base_cals if base_cals > 0 else 500.0
        
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

@router.patch("/{ulid}/status", response_model=dict)
async def update_order_status(ulid: str, req: OrderStatusUpdateRequest, db: AsyncSession = Depends(get_db)):
    order = await db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.ulid == ulid)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    old_status = order.status
    order.status = req.status
    
    if req.status == OrderStatus.DELIVERED and old_status != OrderStatus.DELIVERED:
        from app.tasks.celery_tasks import task_create_calorie_log_on_delivery
        task_create_calorie_log_on_delivery.delay(order.ulid)
            
    await db.commit()
    await db.refresh(order)
    
    return {"success": True, "message": "Status updated successfully", "status": order.status.value}

@router.get("/{ulid}", response_model=dict)
async def get_order(ulid: str, db: AsyncSession = Depends(get_db)):
    order = await db.scalar(
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.bowl)
        )
        .where(Order.ulid == ulid)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = []
    for i in order.items:
        items.append({
            "id": i.id,
            "ulid": i.ulid,
            "bowl_id": i.bowl_id,
            "bowl_name": i.bowl.name if i.bowl else "Unknown",
            "meal_slot": i.meal_slot,
            "quantity": i.quantity,
            "adjusted_calories": float(i.adjusted_calories),
            "adjusted_macros": i.adjusted_macros,
            "adjusted_price": float(i.adjusted_price),
            "adjusted_ingredients": i.adjusted_ingredients,
        })

    customer = order.customer
    customer_data = None
    if customer:
        customer_data = {
            "ulid": customer.ulid,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "goal": customer.goal,
            "calorie_profile": customer.calorie_profile,
        }

    return {
        "success": True,
        "order": {
            "id": order.id,
            "ulid": order.ulid,
            "customer_id": order.customer_id,
            "plan_id": order.plan_id,
            "order_source": order.order_source,
            "status": order.status,
            "target_date": str(order.target_date),
            "total_order_price": float(order.total_order_price),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": items,
            "customer": customer_data,
        }
    }


@router.delete("/{ulid}", response_model=dict)
async def delete_order(ulid: str, db: AsyncSession = Depends(get_db)):
    order = await db.scalar(select(Order).where(Order.ulid == ulid))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.CREATED, OrderStatus.PREPARED):
        raise HTTPException(status_code=400, detail="Only CREATED or PREPARED orders can be deleted")
    await db.delete(order)
    await db.commit()
    return {"success": True, "message": "Order deleted"}


@router.patch("/{ulid}/items/{item_ulid}", response_model=dict)
async def update_order_item(ulid: str, item_ulid: str, req: OrderItemUpdateRequest, db: AsyncSession = Depends(get_db)):
    order = await db.scalar(select(Order).where(Order.ulid == ulid))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.CREATED:
        raise HTTPException(status_code=400, detail="Only CREATED orders can be edited")

    item = await db.scalar(select(OrderItem).where(OrderItem.ulid == item_ulid, OrderItem.order_id == order.id))
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")

    if req.meal_slot is not None:
        item.meal_slot = req.meal_slot
    if req.quantity is not None:
        item.quantity = req.quantity
    if req.adjusted_calories is not None:
        item.adjusted_calories = req.adjusted_calories
    if req.adjusted_price is not None:
        item.adjusted_price = req.adjusted_price
    if req.adjusted_ingredients is not None:
        item.adjusted_ingredients = req.adjusted_ingredients
    if any(v is not None for v in [req.adjusted_protein, req.adjusted_carbs, req.adjusted_fat, req.adjusted_fiber]):
        macros = dict(item.adjusted_macros or {})
        if req.adjusted_protein is not None:
            macros["protein"] = req.adjusted_protein
        if req.adjusted_carbs is not None:
            macros["carbs"] = req.adjusted_carbs
        if req.adjusted_fat is not None:
            macros["fat"] = req.adjusted_fat
        if req.adjusted_fiber is not None:
            macros["fiber"] = req.adjusted_fiber
        item.adjusted_macros = macros

    # Recalculate order total
    all_items = await db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))
    order.total_order_price = sum(float(i.adjusted_price) * i.quantity for i in all_items)

    await db.commit()
    return {"success": True, "message": "Item updated"}
