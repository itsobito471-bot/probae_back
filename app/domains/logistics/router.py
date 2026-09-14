from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.core.database import get_db
from app.domains.logistics.models import Zone, Driver
from app.domains.logistics.schemas import (
    ZoneCreate, ZoneResponse, ZoneUpdate,
    DriverCreate, DriverResponse, DriverUpdate
)

router = APIRouter(prefix="/logistics", tags=["Logistics"])

# =================
# Zones
# =================
@router.get("/zones", response_model=List[ZoneResponse])
async def list_zones(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    query = select(Zone)
    if active_only:
        query = query.where(Zone.is_active == True)
    
    result = await db.execute(query)
    zones = result.scalars().all()
    return zones

@router.post("/zones", response_model=ZoneResponse)
async def create_zone(req: ZoneCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate
    existing = await db.scalar(select(Zone).where(Zone.name == req.name))
    if existing:
        raise HTTPException(status_code=400, detail="Zone with this name already exists")
    
    zone = Zone(
        name=req.name,
        polygon_coordinates=req.polygon_coordinates,
        is_active=req.is_active
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.patch("/zones/{ulid}", response_model=ZoneResponse)
async def update_zone(ulid: str, req: ZoneUpdate, db: AsyncSession = Depends(get_db)):
    zone = await db.scalar(select(Zone).where(Zone.ulid == ulid))
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
        
    if req.name is not None:
        # Check if another zone has this name
        existing = await db.scalar(select(Zone).where(Zone.name == req.name, Zone.id != zone.id))
        if existing:
            raise HTTPException(status_code=400, detail="Another zone with this name already exists")
        zone.name = req.name
        
    if req.polygon_coordinates is not None:
        zone.polygon_coordinates = req.polygon_coordinates
        
    if req.is_active is not None:
        zone.is_active = req.is_active
        
    await db.commit()
    await db.refresh(zone)
    return zone

# =================
# Drivers
# =================
@router.get("/drivers", response_model=List[DriverResponse])
async def list_drivers(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    query = select(Driver)
    if active_only:
        query = query.where(Driver.is_active == True)
        
    result = await db.execute(query)
    drivers = result.scalars().all()
    return drivers

@router.post("/drivers", response_model=DriverResponse)
async def create_driver(req: DriverCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate phone
    existing = await db.scalar(select(Driver).where(Driver.phone == req.phone))
    if existing:
        raise HTTPException(status_code=400, detail="Driver with this phone already exists")
        
    driver = Driver(
        name=req.name,
        phone=req.phone,
        is_active=req.is_active
    )
    db.add(driver)
    await db.commit()
    await db.refresh(driver)
    return driver
