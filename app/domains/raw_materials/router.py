from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, or_
from typing import Optional

from app.core.logging_route import AuditLogRoute
from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User
from app.domains.raw_materials.models import RawMaterial, RawMaterialCategory
from app.domains.raw_materials.schemas import RawMaterialCreate, RawMaterialUpdate, RawMaterialResponse, PaginatedRawMaterials

router = APIRouter(route_class=AuditLogRoute)

@router.post("/", response_model=RawMaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_raw_material(
    material_in: RawMaterialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if name already exists
    result = await db.execute(select(RawMaterial).where(func.lower(RawMaterial.name) == material_in.name.lower()))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Raw material with this name already exists.")

    # Resolve category_ulid to category_id
    category_id = None
    if material_in.category_ulid:
        cat_result = await db.execute(select(RawMaterialCategory).where(RawMaterialCategory.ulid == material_in.category_ulid))
        category = cat_result.scalars().first()
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category ULID.")
        category_id = category.id

    data = material_in.model_dump(exclude={"category_ulid"})
    new_material = RawMaterial(**data, category_id=category_id)
    db.add(new_material)
    await db.commit()
    await db.refresh(new_material)
    
    # Reload with relationships
    result = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category)).where(RawMaterial.id == new_material.id))
    return result.scalars().first()

@router.get("/", response_model=PaginatedRawMaterials)
async def get_raw_materials(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(RawMaterial).options(selectinload(RawMaterial.category))
    
    if search:
        query = query.where(RawMaterial.name.ilike(f"%{search}%"))
        
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Pagination
    query = query.order_by(RawMaterial.name).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "size": size}

@router.get("/{ulid}", response_model=RawMaterialResponse)
async def get_raw_material(ulid: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category)).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")
    return material

@router.patch("/{ulid}", response_model=RawMaterialResponse)
async def update_raw_material(
    ulid: str, 
    material_update: RawMaterialUpdate,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RawMaterial).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")

    update_data = material_update.model_dump(exclude_unset=True)
    if "category_ulid" in update_data:
        cat_ulid = update_data.pop("category_ulid")
        if cat_ulid:
            cat_result = await db.execute(select(RawMaterialCategory).where(RawMaterialCategory.ulid == cat_ulid))
            category = cat_result.scalars().first()
            if not category:
                raise HTTPException(status_code=400, detail="Invalid category ULID.")
            update_data["category_id"] = category.id
        else:
            update_data["category_id"] = None

    for key, value in update_data.items():
        setattr(material, key, value)

    await db.commit()
    await db.refresh(material)
    
    # Reload with relationships
    res = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category)).where(RawMaterial.id == material.id))
    return res.scalars().first()

@router.delete("/{ulid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_raw_material(
    ulid: str, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RawMaterial).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")
    
    await db.delete(material)
    await db.commit()
    return None



from app.domains.raw_materials.schemas import MacrosUpdate

@router.patch("/{ulid}/macros", response_model=RawMaterialResponse)
async def update_raw_material_macros(
    ulid: str, 
    macro_data: MacrosUpdate,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Dedicated endpoint for the Calorie Management module."""
    result = await db.execute(select(RawMaterial).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")

    # Update only the nutritional fields provided
    for key, value in macro_data.model_dump(exclude_unset=True).items():
        setattr(material, key, value)

    await db.commit()
    await db.refresh(material)
    return material