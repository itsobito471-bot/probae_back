from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# Packaging Component Schemas
class PackagingComponentBase(BaseModel):
    name: str
    cost: float

class PackagingComponentCreate(PackagingComponentBase):
    pass

class PackagingComponentUpdate(BaseModel):
    name: Optional[str] = None
    cost: Optional[float] = None

class PackagingComponentResponse(PackagingComponentBase):
    id: int
    ulid: str
    current_stock: float
    stock_threshold: float
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedPackagingComponentResponse(BaseModel):
    items: List[PackagingComponentResponse]
    total: int
    page: int
    page_size: int
    pages: int

# Stock Management Schemas
class PackagingStockAdjustmentRequest(BaseModel):
    quantity_change: float
    description: Optional[str] = None

class PackagingStockThresholdRequest(BaseModel):
    stock_threshold: float

class PackagingComponentStockLogResponse(BaseModel):
    id: int
    ulid: str
    component_id: int
    quantity_change: float
    previous_stock: float
    new_stock: float
    description: Optional[str] = None
    order_ulid: Optional[str] = None
    created_at: datetime
    created_by: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_user(cls, log):
        return cls(
            id=log.id,
            ulid=log.ulid,
            component_id=log.component_id,
            quantity_change=float(log.quantity_change),
            previous_stock=float(log.previous_stock),
            new_stock=float(log.new_stock),
            description=log.description,
            order_ulid=log.order_ulid,
            created_at=log.created_at,
            created_by={"id": log.created_by.id, "name": log.created_by.name} if log.created_by else None,
        )


# Packaging Link Schemas
class PackagingItemLinkInput(BaseModel):
    component_ulid: str
    quantity: int

class PackagingItemLinkResponse(BaseModel):
    component: PackagingComponentResponse
    quantity: int
    
    model_config = ConfigDict(from_attributes=True)

# Packaging Schemas
class PackagingBase(BaseModel):
    name: str
    code: Optional[str] = None

class PackagingCreate(PackagingBase):
    components: List[PackagingItemLinkInput] = []

class PackagingUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    components: Optional[List[PackagingItemLinkInput]] = None

class PackagingResponse(PackagingBase):
    id: int
    ulid: str
    total_cost: float
    components: List[PackagingItemLinkResponse] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedPackagingResponse(BaseModel):
    items: List[PackagingResponse]
    total: int
    page: int
    page_size: int
    pages: int
