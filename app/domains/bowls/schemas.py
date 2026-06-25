from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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

# Minimal Bowl schema just to display in the category preview
class BowlResponse(BaseModel):
    id: int
    ulid: str
    code: Optional[str]
    name: str
    category_id: int

    class Config:
        from_attributes = True

class BowlCategoryResponse(BowlCategoryBase):
    id: int
    ulid: str
    created_at: datetime
    updated_at: datetime
    bowls: List[BowlResponse] = []

    class Config:
        from_attributes = True

class PaginatedBowlCategories(BaseModel):
    items: List[BowlCategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
