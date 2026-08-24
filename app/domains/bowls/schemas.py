from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, time
from app.domains.bowls.models import BowlType, BowlSection

class BowlCategoryBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    image_filename: Optional[str] = None
    background_image_filename: Optional[str] = None

class BowlCategoryCreate(BowlCategoryBase):
    pass

class BowlCategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    image_filename: Optional[str] = None
    background_image_filename: Optional[str] = None

class MealCategoryBase(BaseModel):
    slug: str
    name: str
    color_code: Optional[str] = None
    image_filename: Optional[str] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    is_active: bool = True

class MealCategoryCreate(MealCategoryBase):
    pass

class MealCategoryUpdate(BaseModel):
    name: Optional[str] = None
    color_code: Optional[str] = None
    image_filename: Optional[str] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    is_active: Optional[bool] = None

class MealCategoryResponse(MealCategoryBase):
    id: int
    ulid: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedMealCategories(BaseModel):
    items: List[MealCategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

# Bowl Ingredients
class BowlIngredientInput(BaseModel):
    ingredient_ulid: Optional[str] = None
    ingredient_id: Optional[int] = None
    section_name: BowlSection
    weight_g_or_ml: float

class BowlIngredientResponse(BaseModel):
    ingredient_id: int
    section_name: BowlSection
    weight_g_or_ml: float
    ingredient_ulid: str
    ingredient_name: str
    
    model_config = ConfigDict(from_attributes=True)

class BowlBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    bowl_type: BowlType = BowlType.BLEND
    status: bool = True
    fixed_cost: float = 0.0
    category_id: int
    meal_category_id: Optional[int] = None
    packaging_ulid: Optional[str] = None
    packaging_id: Optional[int] = None
    image_filename: Optional[str] = None

class BowlCreate(BowlBase):
    ingredients: List[BowlIngredientInput] = []

class BowlUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    bowl_type: Optional[BowlType] = None
    status: Optional[bool] = None
    fixed_cost: Optional[float] = None
    category_id: Optional[int] = None
    meal_category_id: Optional[int] = None
    packaging_ulid: Optional[str] = None
    packaging_id: Optional[int] = None
    image_filename: Optional[str] = None
    ingredients: Optional[List[BowlIngredientInput]] = None

class BowlResponse(BaseModel):
    id: int
    ulid: str
    code: Optional[str]
    name: str
    description: Optional[str]
    bowl_type: BowlType
    status: bool
    raw_cost: float
    fixed_cost: float
    total_cost: float
    
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    total_fiber: float = 0.0
    total_weight: float = 0.0
    
    created_at: datetime
    updated_at: datetime
    
    category_id: int
    meal_category_id: Optional[int] = None
    meal_category: Optional[MealCategoryResponse] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    
    packaging_id: Optional[int] = None
    image_filename: Optional[str] = None
    
    # We will resolve the ingredients in the router response to include name and ulid
    ingredients: List[BowlIngredientResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedBowls(BaseModel):
    items: List[BowlResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class BowlCategoryResponse(BowlCategoryBase):
    id: int
    ulid: str
    created_at: datetime
    updated_at: datetime
    bowls: List[BowlResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedBowlCategories(BaseModel):
    items: List[BowlCategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
