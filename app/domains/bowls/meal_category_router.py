import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.domains.bowls.models import MealCategory
from app.domains.bowls.schemas import (
    MealCategoryCreate,
    MealCategoryUpdate,
    MealCategoryResponse,
    PaginatedMealCategories,
)

router = APIRouter()

@router.post("", response_model=MealCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_category(
    category_in: MealCategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MealCategory).filter(MealCategory.slug == category_in.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Meal Category with this slug already exists.")

    new_category = MealCategory(**category_in.model_dump())
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category

@router.get("", response_model=PaginatedMealCategories)
async def list_meal_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(MealCategory)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                MealCategory.name.ilike(search_term),
                MealCategory.slug.ilike(search_term)
            )
        )

    query = query.order_by(MealCategory.name.asc())
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    categories = result.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedMealCategories(
        items=categories,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{ulid}", response_model=MealCategoryResponse)
async def get_meal_category(ulid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MealCategory).filter(MealCategory.ulid == ulid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Meal Category not found")
    return category

@router.patch("/{ulid}", response_model=MealCategoryResponse)
async def update_meal_category(
    ulid: str,
    category_in: MealCategoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MealCategory).filter(MealCategory.ulid == ulid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Meal Category not found")

    update_data = category_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{ulid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_category(ulid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MealCategory).filter(MealCategory.ulid == ulid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Meal Category not found")
        
    await db.delete(category)
    await db.commit()
    return None
