from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.domains.raw_materials.models import UnitType

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
    price: float = Field(..., gt=0, description="Price per unit")
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

class RawMaterialCreate(RawMaterialBase):
    pass

class RawMaterialUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
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

class RawMaterialResponse(RawMaterialBase):
    id: int
    ulid: str
    current_stock: float
    stock_threshold: float
    category: Optional[RawMaterialCategoryResponse] = None
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