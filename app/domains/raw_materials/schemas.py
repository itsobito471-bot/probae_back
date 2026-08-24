from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.domains.raw_materials.models import UnitType
from app.domains.vendors.schemas import VendorResponse

class RawMaterialCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class RawMaterialCategoryCreate(RawMaterialCategoryBase):
    pass

class RawMaterialCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class RawMaterialCategoryResponse(RawMaterialCategoryBase):
    id: int
    ulid: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class PaginatedRawMaterialCategories(BaseModel):
    items: list[RawMaterialCategoryResponse]
    total: int
    page: int
    size: int

class RawMaterialBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0, description="Price per unit (Legacy)")
    standard_price: Optional[float] = Field(None, gt=0, description="Price per unit (Standard)")
    actual_price: Optional[float] = Field(None, gt=0, description="Effective Cost based on Yield")
    yield_grams: Optional[float] = Field(None, gt=0, description="Yield in grams/ml per unit")
    yield_percentage: Optional[float] = Field(None, ge=0, description="Yield Percentage")
    previous_price: Optional[float] = Field(None, description="Previous standard price for variance")
    unit: UnitType
    image_filename: Optional[str] = None
    background_image_filename: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fiber: Optional[float] = None
    fat: Optional[float] = None
    micros: Optional[list[str]] = None
    category_ulid: Optional[str] = None
    vendor_ulid: Optional[str] = None

class RawMaterialCreate(RawMaterialBase):
    pass

class RawMaterialUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    standard_price: Optional[float] = Field(None, gt=0)
    actual_price: Optional[float] = Field(None, gt=0)
    yield_grams: Optional[float] = Field(None, gt=0)
    yield_percentage: Optional[float] = Field(None, ge=0)
    previous_price: Optional[float] = None
    unit: Optional[UnitType] = None
    image_filename: Optional[str] = None
    background_image_filename: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fiber: Optional[float] = None
    fat: Optional[float] = None
    micros: Optional[list[str]] = None
    category_ulid: Optional[str] = None
    vendor_ulid: Optional[str] = None

class RawMaterialResponse(RawMaterialBase):
    id: int
    ulid: str
    current_stock: float
    stock_threshold: float
    category: Optional[RawMaterialCategoryResponse] = None
    vendor: Optional[VendorResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class PaginatedRawMaterials(BaseModel):
    items: list[RawMaterialResponse]
    total: int
    page: int
    size: int


class MacrosUpdate(BaseModel):
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fiber: Optional[float] = None
    fat: Optional[float] = None
    micros: Optional[list[str]] = None

class StockAdjustmentRequest(BaseModel):
    quantity_change: float = Field(..., description="Amount to add (positive) or remove (negative)")
    description: Optional[str] = None

class StockThresholdUpdateRequest(BaseModel):
    stock_threshold: float = Field(..., ge=0)

class UserMini(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str
    
    model_config = {"from_attributes": True}

class StockLogResponse(BaseModel):
    ulid: str
    quantity_change: float
    previous_stock: float
    new_stock: float
    description: Optional[str] = None
    created_at: datetime
    created_by: Optional[UserMini] = None

    model_config = {"from_attributes": True}

class CostLogResponse(BaseModel):
    ulid: str
    previous_standard_price: Optional[float] = None
    new_standard_price: Optional[float] = None
    previous_actual_price: Optional[float] = None
    new_actual_price: Optional[float] = None
    previous_yield_grams: Optional[float] = None
    new_yield_grams: Optional[float] = None
    created_at: datetime
    created_by: Optional[UserMini] = None

    model_config = {"from_attributes": True}

class PaginatedCostLogs(BaseModel):
    items: list[CostLogResponse]
    total: int
    page: int
    size: int
# --- Purchase History Schemas ---
class PurchaseCreate(BaseModel):
    purchase_date: datetime
    raw_material_id: int
    vendor_id: Optional[int] = None
    quantity: float
    unit: UnitType
    standard_cost: float
    actual_price: float
    total_amount: float
    variance: float

class PurchaseResponse(BaseModel):
    id: int
    ulid: str
    purchase_date: datetime
    raw_material_id: int
    vendor_id: Optional[int] = None
    quantity: float
    unit: UnitType
    standard_cost: float
    actual_price: float
    total_amount: float
    variance: float
    created_at: datetime
    updated_at: datetime
    
    raw_material: Optional['RawMaterialResponse'] = None
    vendor: Optional[VendorResponse] = None

    model_config = {"from_attributes": True}

class PaginatedPurchases(BaseModel):
    items: list[PurchaseResponse]
    total: int
    page: int
    size: int
