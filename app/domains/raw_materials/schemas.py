from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.domains.raw_materials.models import UnitType

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

class RawMaterialResponse(RawMaterialBase):
    id: int
    ulid: str
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