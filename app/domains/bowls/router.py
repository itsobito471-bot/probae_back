import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.domains.bowls.models import BowlCategory, Bowl
from app.domains.bowls.schemas import (
    BowlCategoryCreate,
    BowlCategoryUpdate,
    BowlCategoryResponse,
    PaginatedBowlCategories,
)

router = APIRouter()

@router.post("", response_model=BowlCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_bowl_category(
    category_in: BowlCategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check code uniqueness if provided
    if category_in.code:
        result = await db.execute(select(BowlCategory).filter(BowlCategory.code == category_in.code))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bowl Category with this code already exists.")
            
    # Check name uniqueness
    result = await db.execute(select(BowlCategory).filter(BowlCategory.name == category_in.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bowl Category with this name already exists.")

    new_category = BowlCategory(**category_in.model_dump())
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    
    # Reload with bowls to satisfy response model
    result = await db.execute(
        select(BowlCategory)
        .options(selectinload(BowlCategory.bowls))
        .filter(BowlCategory.id == new_category.id)
    )
    return result.scalar_one()

@router.get("", response_model=PaginatedBowlCategories)
async def list_bowl_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_db)
):
    query = select(BowlCategory).options(selectinload(BowlCategory.bowls))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                BowlCategory.name.ilike(search_term),
                BowlCategory.code.ilike(search_term),
                BowlCategory.description.ilike(search_term)
            )
        )

    # Sorting
    if sort_by == "name":
        order_col = BowlCategory.name
    elif sort_by == "code":
        order_col = BowlCategory.code
    elif sort_by == "created_at":
        order_col = BowlCategory.created_at
    else:
        order_col = BowlCategory.name

    if sort_order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    categories = result.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedBowlCategories(
        items=categories,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{ulid}", response_model=BowlCategoryResponse)
async def get_bowl_category(ulid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BowlCategory)
        .options(selectinload(BowlCategory.bowls))
        .filter(BowlCategory.ulid == ulid)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Bowl Category not found")
    return category

@router.put("/{ulid}", response_model=BowlCategoryResponse)
async def update_bowl_category(
    ulid: str,
    category_in: BowlCategoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BowlCategory)
        .options(selectinload(BowlCategory.bowls))
        .filter(BowlCategory.ulid == ulid)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Bowl Category not found")

    update_data = category_in.model_dump(exclude_unset=True)
    
    if "code" in update_data and update_data["code"] != category.code:
        code_check = await db.execute(select(BowlCategory).filter(BowlCategory.code == update_data["code"]))
        if code_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Another Bowl Category with this code already exists.")
            
    if "name" in update_data and update_data["name"] != category.name:
        name_check = await db.execute(select(BowlCategory).filter(BowlCategory.name == update_data["name"]))
        if name_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Another Bowl Category with this name already exists.")

    for key, value in update_data.items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{ulid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bowl_category(ulid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BowlCategory).filter(BowlCategory.ulid == ulid))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Bowl Category not found")
        
    await db.delete(category)
    await db.commit()
    return None
