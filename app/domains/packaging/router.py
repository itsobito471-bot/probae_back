import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User
from .models import PackagingComponent, Packaging, PackagingItemLink, PackagingComponentStockLog
from .schemas import (
    PackagingComponentCreate, PackagingComponentUpdate, PackagingComponentResponse, PaginatedPackagingComponentResponse,
    PackagingCreate, PackagingUpdate, PackagingResponse, PaginatedPackagingResponse,
    PackagingStockAdjustmentRequest, PackagingStockThresholdRequest, PackagingComponentStockLogResponse,
)

router = APIRouter()

# --- Packaging Components ---
@router.post("/components", response_model=PackagingComponentResponse, status_code=201)
async def create_packaging_component(
    payload: PackagingComponentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = await db.scalar(select(PackagingComponent).where(PackagingComponent.name == payload.name))
    if existing:
        raise HTTPException(status_code=400, detail="Component with this name already exists")
        
    comp = PackagingComponent(name=payload.name, cost=payload.cost)
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return comp

@router.get("/components", response_model=PaginatedPackagingComponentResponse)
async def list_packaging_components(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(PackagingComponent)
    if search:
        query = query.where(PackagingComponent.name.ilike(f"%{search}%"))
        
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(PackagingComponent.id.desc()).offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    pages = math.ceil(total / page_size) if total else 0
    
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}

@router.put("/components/{ulid}", response_model=PackagingComponentResponse)
async def update_packaging_component(
    ulid: str,
    payload: PackagingComponentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comp = await db.scalar(select(PackagingComponent).where(PackagingComponent.ulid == ulid))
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
        
    if payload.name is not None and payload.name != comp.name:
        existing = await db.scalar(select(PackagingComponent).where(PackagingComponent.name == payload.name))
        if existing:
            raise HTTPException(status_code=400, detail="Component with this name already exists")
        comp.name = payload.name
        
    if payload.cost is not None:
        comp.cost = payload.cost
        
    await db.commit()
    await db.refresh(comp)
    return comp

@router.delete("/components/{ulid}", status_code=204)
async def delete_packaging_component(
    ulid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comp = await db.scalar(select(PackagingComponent).where(PackagingComponent.ulid == ulid))
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
    await db.delete(comp)
    await db.commit()

# --- Packaging Component Stock ---

@router.post("/components/{ulid}/stock", response_model=PackagingComponentResponse)
async def adjust_packaging_component_stock(
    ulid: str,
    adjustment: PackagingStockAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually add or remove stock from a packaging component and log the transaction."""
    comp = await db.scalar(select(PackagingComponent).where(PackagingComponent.ulid == ulid))
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")

    previous_stock = float(comp.current_stock)
    new_stock = previous_stock + adjustment.quantity_change

    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot go below zero.")

    comp.current_stock = new_stock

    log = PackagingComponentStockLog(
        component_id=comp.id,
        quantity_change=adjustment.quantity_change,
        previous_stock=previous_stock,
        new_stock=new_stock,
        description=adjustment.description,
        created_by_id=current_user.id,
    )
    db.add(log)
    await db.commit()
    await db.refresh(comp)
    return comp


@router.patch("/components/{ulid}/stock-threshold", response_model=PackagingComponentResponse)
async def update_packaging_component_threshold(
    ulid: str,
    data: PackagingStockThresholdRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the low-stock threshold for a packaging component."""
    comp = await db.scalar(select(PackagingComponent).where(PackagingComponent.ulid == ulid))
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
    comp.stock_threshold = data.stock_threshold
    await db.commit()
    await db.refresh(comp)
    return comp


@router.get("/components/{ulid}/stock-logs")
async def get_packaging_component_stock_logs(
    ulid: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated stock log history for a packaging component."""
    comp = await db.scalar(select(PackagingComponent).where(PackagingComponent.ulid == ulid))
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")

    count = await db.scalar(
        select(func.count()).select_from(
            select(PackagingComponentStockLog).where(PackagingComponentStockLog.component_id == comp.id).subquery()
        )
    )

    logs_result = await db.execute(
        select(PackagingComponentStockLog)
        .options(selectinload(PackagingComponentStockLog.created_by))
        .where(PackagingComponentStockLog.component_id == comp.id)
        .order_by(PackagingComponentStockLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    logs = logs_result.scalars().all()

    return {
        "items": [PackagingComponentStockLogResponse.from_orm_with_user(l) for l in logs],
        "total": count,
        "page": page,
        "size": size,
    }

# --- Packaging Bundles ---
@router.post("/", response_model=PackagingResponse, status_code=201)
async def create_packaging(
    payload: PackagingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = await db.scalar(select(Packaging).where(Packaging.name == payload.name))
    if existing:
        raise HTTPException(status_code=400, detail="Packaging bundle with this name already exists")
        
    pack = Packaging(name=payload.name, code=payload.code, total_cost=0)
    db.add(pack)
    await db.flush()
    
    for item in payload.components:
        comp = await db.scalar(select(PackagingComponent).where(PackagingComponent.ulid == item.component_ulid))
        if not comp:
            raise HTTPException(status_code=404, detail=f"Component {item.component_ulid} not found")
        
        pack.total_cost += (float(comp.cost) * item.quantity)
        link = PackagingItemLink(packaging_id=pack.id, component_id=comp.id, quantity=item.quantity)
        db.add(link)
        
    await db.commit()
    
    result = await db.execute(select(Packaging).options(selectinload(Packaging.components).selectinload(PackagingItemLink.component)).where(Packaging.id == pack.id))
    return result.scalar_one()

@router.get("/", response_model=PaginatedPackagingResponse)
async def list_packaging(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Packaging)
    if search:
        query = query.where(Packaging.name.ilike(f"%{search}%"))
        
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(Packaging.id.desc()).offset((page - 1) * page_size).limit(page_size)
    query = query.options(selectinload(Packaging.components).selectinload(PackagingItemLink.component))
    
    result = await db.execute(query)
    items = result.scalars().all()
    pages = math.ceil(total / page_size) if total else 0
    
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}

@router.get("/{ulid}", response_model=PackagingResponse)
async def get_packaging(
    ulid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Packaging)
        .options(selectinload(Packaging.components).selectinload(PackagingItemLink.component))
        .where(Packaging.ulid == ulid)
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Packaging not found")
    return pack

@router.put("/{ulid}", response_model=PackagingResponse)
async def update_packaging(
    ulid: str,
    payload: PackagingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Packaging)
        .options(selectinload(Packaging.components).selectinload(PackagingItemLink.component))
        .where(Packaging.ulid == ulid)
    )
    pack = result.scalar_one_or_none()
    if not pack:
        raise HTTPException(status_code=404, detail="Packaging not found")
        
    if payload.name is not None and payload.name != pack.name:
        existing = await db.scalar(select(Packaging).where(Packaging.name == payload.name))
        if existing:
            raise HTTPException(status_code=400, detail="Packaging bundle with this name already exists")
        pack.name = payload.name
        
    if payload.code is not None:
        pack.code = payload.code
    if payload.components is not None:
        await db.execute(PackagingItemLink.__table__.delete().where(PackagingItemLink.packaging_id == pack.id))
        
        pack.total_cost = 0
        for item in payload.components:
            comp = await db.scalar(select(PackagingComponent).where(PackagingComponent.ulid == item.component_ulid))
            if not comp:
                raise HTTPException(status_code=404, detail=f"Component {item.component_ulid} not found")
            
            pack.total_cost += (float(comp.cost) * item.quantity)
            link = PackagingItemLink(packaging_id=pack.id, component_id=comp.id, quantity=item.quantity)
            db.add(link)
            
    await db.commit()
    result = await db.execute(select(Packaging).options(selectinload(Packaging.components).selectinload(PackagingItemLink.component)).where(Packaging.id == pack.id))
    return result.scalar_one()

@router.delete("/{ulid}", status_code=204)
async def delete_packaging(
    ulid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pack = await db.scalar(select(Packaging).where(Packaging.ulid == ulid))
    if not pack:
        raise HTTPException(status_code=404, detail="Packaging not found")
    await db.delete(pack)
    await db.commit()
