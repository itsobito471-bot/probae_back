from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class CustomerStatus(str, Enum):
    ONBOARDING = "ONBOARDING"
    PENDING_PLAN = "PENDING_PLAN"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class CalorieProfileSchema(BaseModel):
    total: int
    protein: int
    carbs: int
    fat: int
    fiber: int
    probaeTarget: Optional[int] = None
    mealCalories: Optional[Dict[str, int]] = None
    lockedMeals: Optional[Dict[str, bool]] = None
    mealSlots: Optional[List[str]] = None

class CustomerBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    image_filename: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    sex: str
    age: int
    height: float
    weight: float
    activity_level: str
    goal: str
    
    dietary_preferences: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    chef_instructions: Optional[str] = None
    
    calorie_profile: Optional[CalorieProfileSchema] = None
    selected_plan_id: Optional[str] = None
    status: Optional[CustomerStatus] = CustomerStatus.ONBOARDING
    total_calories_ordered: Optional[float] = 0.0

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    image_filename: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sex: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_level: Optional[str] = None
    goal: Optional[str] = None
    dietary_preferences: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    chef_instructions: Optional[str] = None
    calorie_profile: Optional[CalorieProfileSchema] = None
    selected_plan_id: Optional[str] = None
    status: Optional[CustomerStatus] = None

class CustomerOut(CustomerBase):
    ulid: str
    
    class Config:
        orm_mode = True
        from_attributes = True

class CalculateCaloriesRequest(BaseModel):
    sex: str
    age: int
    height: float
    weight: float
    activity_level: str
    goal: str
