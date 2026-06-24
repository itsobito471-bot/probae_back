from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Optional

from app.core.logging_route import AuditLogRoute
from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User
from app.domains.raw_materials.models import RawMaterialCategory
from app.domains.raw_materials.schemas import (
    RawMaterialCategoryCreate,
    RawMaterialCategoryUpdate,
    RawMaterialCategoryResponse,
    PaginatedRawMaterialCategories,
)

router = APIRouter(route_class=AuditLogRoute)

@router.post("/", response_model=RawMaterialCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: RawMaterialCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RawMaterialCategory).where(func.lower(RawMaterialCategory.name) == category_in.name.lower()))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Category with this name already exists.")

    new_category = RawMaterialCategory(**category_in.model_dump())
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category

@router.get("/", response_model=PaginatedRawMaterialCategories)
async def get_categories(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(RawMaterialCategory)
    
    if search:
        query = query.where(RawMaterialCategory.name.ilike(f"%{search}%"))
        
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(RawMaterialCategory.name).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "size": size}

@router.get("/{ulid}", response_model=RawMaterialCategoryResponse)
async def get_category(ulid: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RawMaterialCategory).where(RawMaterialCategory.ulid == ulid))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.patch("/{ulid}", response_model=RawMaterialCategoryResponse)
async def update_category(
    ulid: str, 
    category_update: RawMaterialCategoryUpdate,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RawMaterialCategory).where(RawMaterialCategory.ulid == ulid))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category_update.name:
        name_check = await db.execute(select(RawMaterialCategory).where(func.lower(RawMaterialCategory.name) == category_update.name.lower(), RawMaterialCategory.ulid != ulid))
        if name_check.scalars().first():
            raise HTTPException(status_code=400, detail="Category with this name already exists.")

    for key, value in category_update.model_dump(exclude_unset=True).items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{ulid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    ulid: str, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RawMaterialCategory).where(RawMaterialCategory.ulid == ulid))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    await db.delete(category)
    await db.commit()
    return None
