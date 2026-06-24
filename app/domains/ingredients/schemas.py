from pydantic import BaseModel, Field, constr
from typing import Optional, List
from datetime import datetime

class RawMaterialWeightInput(BaseModel):
    raw_material_id: int
    weight_g_or_ml: float = Field(..., gt=0, description="Weight used in grams or ml")

class IngredientRawMaterialResponse(BaseModel):
    id: int
    raw_material_id: int
    weight_g_or_ml: float
    
    class Config:
        from_attributes = True

class IngredientCreate(BaseModel):
    code: Optional[str] = None
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    image_filename: Optional[str] = None
    background_image_filename: Optional[str] = None
    raw_materials: List[RawMaterialWeightInput] = []

class IngredientUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    image_filename: Optional[str] = None
    background_image_filename: Optional[str] = None
    raw_materials: Optional[List[RawMaterialWeightInput]] = None

class IngredientResponse(BaseModel):
    id: int
    ulid: str
    code: Optional[str]
    name: str
    description: Optional[str]
    image_filename: Optional[str]
    background_image_filename: Optional[str]
    
    total_weight: float
    total_price: float
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    
    created_at: datetime
    updated_at: datetime
    
    raw_materials: List[IngredientRawMaterialResponse] = []

    class Config:
        from_attributes = True

class PaginatedIngredientResponse(BaseModel):
    items: List[IngredientResponse]
    total: int
    page: int
    page_size: int
    pages: int
