from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.database import get_db
from app.domains.customers.models import Customer, CustomerStatus
from app.domains.customers.schemas import (
    CustomerCreate, CustomerUpdate, CustomerOut, CalculateCaloriesRequest, CalorieProfileSchema
)
from typing import List
import math

router = APIRouter(prefix="/customers", tags=["Customers"])

def calculate_mifflin(data: CalculateCaloriesRequest) -> dict:
    weight = data.weight
    height = data.height
    age = data.age
    is_male = data.sex.lower() == "male"
    
    # BMR
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + (5 if is_male else -161)
    
    # Activity Multiplier
    activity_multiplier = 1.2
    al = data.activity_level.lower()
    if al == "lightly active":
        activity_multiplier = 1.375
    elif al == "active":
        activity_multiplier = 1.55
    elif al in ["very active", "athlete"]:
        activity_multiplier = 1.725
        
    tdee = bmr * activity_multiplier
    
    # Goal Adjustment
    g = data.goal.lower()
    if "loss" in g:
        tdee -= 500
    elif "gain" in g:
        tdee += 300
        
    if is_male and tdee < 1500: tdee = 1500
    if not is_male and tdee < 1200: tdee = 1200
    tdee = round(tdee)
    
    # Macros
    protein_factor = 1.6
    if al in ["sedentary", "lightly active"]:
        if "maintain" in g or "loss" in g:
            protein_factor = 0.8 if al == "sedentary" else 1.0
        else:
            protein_factor = 1.6
    elif al == "active":
        protein_factor = 1.5
    elif al in ["very active", "athlete"]:
        protein_factor = 2.0
        
    protein = round(weight * protein_factor)
    fat = round((tdee * 0.25) / 9)
    protein_cals = protein * 4
    fat_cals = fat * 9
    carbs = max(0, round((tdee - protein_cals - fat_cals) / 4))
    fiber = round((tdee / 1000) * 14)
    
    return {
        "total": tdee,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "fiber": fiber
    }

@router.post("/calculate-calories", response_model=CalorieProfileSchema)
async def calculate_calories(req: CalculateCaloriesRequest):
    return calculate_mifflin(req)

@router.post("", response_model=CustomerOut)
async def create_customer(customer_in: CustomerCreate, db: AsyncSession = Depends(get_db)):
    # Check if phone exists
    res = await db.execute(select(Customer).where(Customer.phone == customer_in.phone))
    existing = res.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="A customer with this phone number already exists.")

    # Calculate profile if not provided
    if not customer_in.calorie_profile:
        calc_req = CalculateCaloriesRequest(
            sex=customer_in.sex, age=customer_in.age, height=customer_in.height,
            weight=customer_in.weight, activity_level=customer_in.activity_level, goal=customer_in.goal
        )
        customer_in.calorie_profile = calculate_mifflin(calc_req)
        
    new_customer = Customer(**customer_in.dict())
    db.add(new_customer)
    try:
        await db.commit()
        await db.refresh(new_customer)
        return new_customer
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=dict)
async def list_customers(
    page: int = 1,
    limit: int = 10,
    search: str = "",
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * limit
    query = select(Customer)
    if search:
        query = query.where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%")
            )
        )
    
    total_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(total_query)
    total_count = total_res.scalar() or 0
    
    query = query.order_by(Customer.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    customers = res.scalars().all()
    
    return {
        "success": True,
        "customers": [CustomerOut.model_validate(c).model_dump(mode="json") for c in customers],
        "totalCount": total_count,
        "page": page,
        "limit": limit
    }

@router.get("/{ulid}", response_model=CustomerOut)
async def get_customer(ulid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Customer).where(Customer.ulid == ulid))
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c

@router.patch("/{ulid}", response_model=CustomerOut)
async def update_customer(ulid: str, customer_in: CustomerUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Customer).where(Customer.ulid == ulid))
    customer = res.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    update_data = customer_in.model_dump(exclude_unset=True)
    
    # If phone is being updated, check for duplicates
    if "phone" in update_data and update_data["phone"] != customer.phone:
        phone_check = await db.execute(select(Customer).where(Customer.phone == update_data["phone"]))
        if phone_check.scalars().first():
            raise HTTPException(status_code=400, detail="A customer with this phone number already exists.")
            
    # Auto-recalculate calories if biological factors change
    bio_keys = ["sex", "age", "height", "weight", "activity_level", "goal"]
    if any(k in update_data for k in bio_keys) and "calorie_profile" not in update_data:
        calc_req = CalculateCaloriesRequest(
            sex=update_data.get("sex", customer.sex),
            age=update_data.get("age", customer.age),
            height=update_data.get("height", customer.height),
            weight=update_data.get("weight", customer.weight),
            activity_level=update_data.get("activity_level", customer.activity_level),
            goal=update_data.get("goal", customer.goal)
        )
        update_data["calorie_profile"] = calculate_mifflin(calc_req)
    
    for field, value in update_data.items():
        setattr(customer, field, value)
        
    try:
        await db.commit()
        await db.refresh(customer)
        return customer
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{ulid}")
async def delete_customer(ulid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Customer).where(Customer.ulid == ulid))
    customer = res.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    await db.delete(customer)
    await db.commit()
    return {"success": True, "message": "Customer deleted successfully"}
