from pydantic import BaseModel, Field
from typing import List, Optional

class BowlBasicSchema(BaseModel):
    id: int
    ulid: str
    name: str
    base_price: float = Field(alias="total_cost")
    base_calories: float = Field(alias="raw_cost") # fallback
    
    class Config:
        populate_by_name = True
        from_attributes = True

class TierSelectionSchema(BaseModel):
    type: str
    bowls: List[str] # List of bowl ULIDs when reading, or Bowl objects if we want

class TierSelectionResponse(BaseModel):
    type: str
    bowls: List[BowlBasicSchema]
    
    class Config:
        from_attributes = True

class PlanTierCreate(BaseModel):
    name: str
    category: str
    duration: str
    days: int
    mealType: str
    totalPrice: float
    discountPrice: Optional[float] = 0.0
    selections: List[TierSelectionSchema]

class PlanTierUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    duration: Optional[str] = None
    days: Optional[int] = None
    mealType: Optional[str] = None
    totalPrice: Optional[float] = None
    discountPrice: Optional[float] = None
    selections: Optional[List[TierSelectionSchema]] = None

class PlanTierResponse(BaseModel):
    id: int
    ulid: str
    name: str
    category: str
    duration: str
    days: int
    mealType: str
    totalPrice: float
    discountPrice: float
    selections: Optional[List[TierSelectionResponse]] = None
    
    class Config:
        from_attributes = True
        
class PlanTierListResponse(BaseModel):
    success: bool = True
    tiers: List[PlanTierResponse]
    totalCount: int
    page: int
    limit: int
