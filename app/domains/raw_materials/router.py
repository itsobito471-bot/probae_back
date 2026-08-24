from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, or_, cast, extract, Date
from typing import Optional

from app.core.logging_route import AuditLogRoute
from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User
from app.domains.raw_materials.models import RawMaterial, RawMaterialCategory, RawMaterialPurchase, RawMaterialStockLog
from app.domains.vendors.models import Vendor
from app.domains.raw_materials.schemas import RawMaterialCreate, RawMaterialUpdate, RawMaterialResponse, PaginatedRawMaterials, StockAdjustmentRequest, StockThresholdUpdateRequest, StockLogResponse, CostLogResponse, PaginatedCostLogs

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

    # Resolve vendor_ulid to vendor_id
    vendor_id = None
    if material_in.vendor_ulid:
        vendor_result = await db.execute(select(Vendor).where(Vendor.ulid == material_in.vendor_ulid))
        vendor = vendor_result.scalars().first()
        if not vendor:
            raise HTTPException(status_code=400, detail="Invalid vendor ULID.")
        vendor_id = vendor.id

    data = material_in.model_dump(exclude={"category_ulid", "vendor_ulid"})
    
    # Initialize previous_price to standard_price if not provided
    if "standard_price" in data and data["standard_price"] is not None:
        if "previous_price" not in data or data["previous_price"] is None:
            data["previous_price"] = data["standard_price"]

    new_material = RawMaterial(**data, category_id=category_id, vendor_id=vendor_id)
    db.add(new_material)
    await db.commit()
    await db.refresh(new_material)
    
    # Reload with relationships
    result = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category), selectinload(RawMaterial.vendor)).where(RawMaterial.id == new_material.id))
    return result.scalars().first()

@router.get("/", response_model=PaginatedRawMaterials)
async def get_raw_materials(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(RawMaterial).options(selectinload(RawMaterial.category), selectinload(RawMaterial.vendor))
    
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

@router.get("/metrics/low-stock-count")
async def get_low_stock_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(func.count()).select_from(RawMaterial).where(RawMaterial.current_stock <= RawMaterial.stock_threshold)
    result = await db.execute(query)
    count = result.scalar()
    return {"count": count}

@router.get("/{ulid}", response_model=RawMaterialResponse)
async def get_raw_material(ulid: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category), selectinload(RawMaterial.vendor)).where(RawMaterial.ulid == ulid))
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
            
    if "vendor_ulid" in update_data:
        vendor_ulid = update_data.pop("vendor_ulid")
        if vendor_ulid:
            vendor_result = await db.execute(select(Vendor).where(Vendor.ulid == vendor_ulid))
            vendor = vendor_result.scalars().first()
            if not vendor:
                raise HTTPException(status_code=400, detail="Invalid vendor ULID.")
            update_data["vendor_id"] = vendor.id
        else:
            update_data["vendor_id"] = None

    # Track changes for Cost Log
    cost_fields = ['standard_price', 'actual_price', 'yield_grams']
    cost_changed = any(k in update_data and update_data[k] != getattr(material, k) for k in cost_fields)
    
    if cost_changed:
        from app.domains.raw_materials.models import RawMaterialCostLog

        log_entry = RawMaterialCostLog(
            raw_material_id=material.id,
            previous_standard_price=material.standard_price,
            new_standard_price=update_data.get(
                'standard_price',
                material.standard_price
            ),
            previous_actual_price=material.actual_price,
            new_actual_price=update_data.get(
                'actual_price',
                material.actual_price
            ),
            previous_yield_grams=material.yield_grams,
            new_yield_grams=update_data.get(
                'yield_grams',
                material.yield_grams
            ),
            created_by_id=current_user.id
        )

        db.add(log_entry)

        print("Before cost log flush")
        await db.flush()
        print("Cost log flush successful")


    for key, value in update_data.items():
        setattr(material, key, value)

    print("Before raw material flush")
    await db.flush()
    print("Raw material flush successful")

    await db.commit()
    await db.refresh(material)
    
    # Reload with relationships
    res = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category), selectinload(RawMaterial.vendor)).where(RawMaterial.id == material.id))
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
    
    # Reload with category for response
    res = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category)).where(RawMaterial.id == material.id))
    return res.scalars().first()

@router.post("/{ulid}/stock", response_model=RawMaterialResponse)
async def adjust_raw_material_stock(
    ulid: str,
    adjustment: StockAdjustmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add or remove stock and log the transaction."""
    result = await db.execute(select(RawMaterial).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")

    previous_stock = material.current_stock
    new_stock = float(previous_stock) + adjustment.quantity_change
    
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative.")

    material.current_stock = new_stock
    
    log_entry = RawMaterialStockLog(
        raw_material_id=material.id,
        quantity_change=adjustment.quantity_change,
        previous_stock=previous_stock,
        new_stock=new_stock,
        description=adjustment.description,
        created_by_id=current_user.id
    )
    db.add(log_entry)
    
    await db.commit()
    await db.refresh(material)
    
    # Reload with category for response
    res = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category)).where(RawMaterial.id == material.id))
    return res.scalars().first()


@router.patch("/{ulid}/stock-threshold", response_model=RawMaterialResponse)
async def update_stock_threshold(
    ulid: str,
    threshold_data: StockThresholdUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update stock threshold."""
    result = await db.execute(select(RawMaterial).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")

    material.stock_threshold = threshold_data.stock_threshold
    
    await db.commit()
    await db.refresh(material)
    
    # Reload with category for response
    res = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.category)).where(RawMaterial.id == material.id))
    return res.scalars().first()


@router.get("/{ulid}/stock-logs", response_model=list[StockLogResponse])
async def get_raw_material_stock_logs(
    ulid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get stock transaction history for a raw material."""
    result = await db.execute(select(RawMaterial).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")

    logs_result = await db.execute(
        select(RawMaterialStockLog)
        .options(selectinload(RawMaterialStockLog.created_by))
        .where(RawMaterialStockLog.raw_material_id == material.id)
        .order_by(RawMaterialStockLog.created_at.desc())
    )
    logs = logs_result.scalars().all()
    
    return logs


@router.get("/{ulid}/cost-logs", response_model=PaginatedCostLogs)
async def get_raw_material_cost_logs(
    ulid: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cost transaction history for a raw material."""
    result = await db.execute(select(RawMaterial).where(RawMaterial.ulid == ulid))
    material = result.scalars().first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")

    from app.domains.raw_materials.models import RawMaterialCostLog
    
    query = select(RawMaterialCostLog).where(RawMaterialCostLog.raw_material_id == material.id)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    logs_result = await db.execute(
        query
        .options(selectinload(RawMaterialCostLog.created_by))
        .order_by(RawMaterialCostLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    logs = logs_result.scalars().all()
    
    return {
        "items": logs,
        "total": total,
        "page": page,
        "size": size
    }

from app.domains.raw_materials.schemas import PurchaseCreate, PurchaseResponse, PaginatedPurchases

@router.post("/purchases/batch", response_model=list[PurchaseResponse])
async def create_purchases(
    purchases_in: list[PurchaseCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_purchases = []
    rm_ids = [p.raw_material_id for p in purchases_in]
    res = await db.execute(select(RawMaterial).where(RawMaterial.id.in_(rm_ids)))
    raw_materials = {rm.id: rm for rm in res.scalars().all()}

    for p_in in purchases_in:
        rm = raw_materials.get(p_in.raw_material_id)
        if not rm:
            raise HTTPException(status_code=404, detail=f"Raw material {p_in.raw_material_id} not found")
            
        db_purchase = RawMaterialPurchase(
            **p_in.model_dump(),
            created_by_id=current_user.id
        )
        db.add(db_purchase)
        new_purchases.append(db_purchase)
        
        # Update stock
        prev_stock = rm.current_stock
        rm.current_stock = float(rm.current_stock) + float(p_in.quantity)
        new_stock = rm.current_stock
        
        # Log stock change
        stock_log = RawMaterialStockLog(
            raw_material_id=rm.id,
            quantity_change=p_in.quantity,
            previous_stock=prev_stock,
            new_stock=new_stock,
            description="Purchase Restock",
            created_by_id=current_user.id
        )
        db.add(stock_log)
    
    await db.commit()
    for p in new_purchases:
        await db.refresh(p)
    
    # Need to load relationships for response
    q = select(RawMaterialPurchase).where(
        RawMaterialPurchase.id.in_([p.id for p in new_purchases])
    ).options(
        selectinload(RawMaterialPurchase.raw_material).selectinload(RawMaterial.category), selectinload(RawMaterialPurchase.raw_material).selectinload(RawMaterial.vendor),
        selectinload(RawMaterialPurchase.vendor)
    )
    res = await db.execute(q)
    return res.scalars().all()

@router.delete("/purchases/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    purchase = await db.get(RawMaterialPurchase, id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
        
    rm = await db.get(RawMaterial, purchase.raw_material_id)
    if rm:
        prev_stock = rm.current_stock
        rm.current_stock = float(rm.current_stock) - float(purchase.quantity)
        new_stock = rm.current_stock
        
        stock_log = RawMaterialStockLog(
            raw_material_id=rm.id,
            quantity_change=-float(purchase.quantity),
            previous_stock=prev_stock,
            new_stock=new_stock,
            description="Purchase Record Deleted",
            created_by_id=current_user.id
        )
        db.add(stock_log)
        
    await db.delete(purchase)
    await db.commit()


@router.get("/purchases/daily", response_model=PaginatedPurchases)
async def get_daily_purchases(
    date: str, # Format: YYYY-MM-DD
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from datetime import datetime
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    
    q = select(RawMaterialPurchase).where(
        cast(RawMaterialPurchase.purchase_date, Date) == target_date
    )
    
    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()
    
    q = q.options(
        selectinload(RawMaterialPurchase.raw_material).selectinload(RawMaterial.category), selectinload(RawMaterialPurchase.raw_material).selectinload(RawMaterial.vendor),
        selectinload(RawMaterialPurchase.vendor)
    ).order_by(RawMaterialPurchase.purchase_date.desc()).offset((page - 1) * size).limit(size)
    
    res = await db.execute(q)
    items = res.scalars().all()
    
    return PaginatedPurchases(
        items=items,
        total=total,
        page=page,
        size=size
    )

@router.get("/purchases/monthly", response_model=PaginatedPurchases)
async def get_monthly_purchases(
    month: str, # Format: YYYY-MM
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy import extract
    
    year_str, month_str = month.split('-')
    target_year = int(year_str)
    target_month = int(month_str)
    
    q = select(RawMaterialPurchase).where(
        extract('year', RawMaterialPurchase.purchase_date) == target_year,
        extract('month', RawMaterialPurchase.purchase_date) == target_month
    )
    
    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()
    
    q = q.options(
        selectinload(RawMaterialPurchase.raw_material).selectinload(RawMaterial.category), selectinload(RawMaterialPurchase.raw_material).selectinload(RawMaterial.vendor),
        selectinload(RawMaterialPurchase.vendor)
    ).order_by(RawMaterialPurchase.purchase_date.desc()).offset((page - 1) * size).limit(size)
    
    res = await db.execute(q)
    items = res.scalars().all()
    
    return PaginatedPurchases(
        items=items,
        total=total,
        page=page,
        size=size
    )
