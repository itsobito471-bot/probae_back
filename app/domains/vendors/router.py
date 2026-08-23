import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User
from .models import Vendor
from .schemas import (
    VendorCreate, VendorUpdate, VendorResponse, PaginatedVendorResponse
)

router = APIRouter()

@router.post("/", response_model=VendorResponse, status_code=201)
async def create_vendor(
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = await db.scalar(select(Vendor).where(Vendor.name == payload.name))
    if existing:
        raise HTTPException(status_code=400, detail="Vendor with this name already exists")
        
    vendor = Vendor(
        name=payload.name,
        description=payload.description
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor

@router.get("/", response_model=PaginatedVendorResponse)
async def list_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Vendor)
    if search:
        query = query.where(
            (Vendor.name.ilike(f"%{search}%")) |
            (Vendor.code.ilike(f"%{search}%"))
        )
        
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(Vendor.name.asc()).offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    pages = math.ceil(total / page_size) if total else 0
    
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}

@router.get("/{ulid}", response_model=VendorResponse)
async def get_vendor(
    ulid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    vendor = await db.scalar(select(Vendor).where(Vendor.ulid == ulid))
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor

@router.put("/{ulid}", response_model=VendorResponse)
async def update_vendor(
    ulid: str,
    payload: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    vendor = await db.scalar(select(Vendor).where(Vendor.ulid == ulid))
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    if payload.name is not None and payload.name != vendor.name:
        existing = await db.scalar(select(Vendor).where(Vendor.name == payload.name))
        if existing:
            raise HTTPException(status_code=400, detail="Vendor with this name already exists")
        vendor.name = payload.name
        
    if payload.description is not None:
        vendor.description = payload.description
        
    await db.commit()
    await db.refresh(vendor)
    return vendor

@router.delete("/{ulid}", status_code=204)
async def delete_vendor(
    ulid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    vendor = await db.scalar(select(Vendor).where(Vendor.ulid == ulid))
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    # Check if used in raw materials (will add logic later or rely on DB constraint)
    # Ideally should check or just let SQLAlchemy foreign key ON DELETE restrict handle it.
    
    await db.delete(vendor)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete vendor, it may be in use.")
