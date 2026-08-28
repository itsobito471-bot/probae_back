from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date
from .models import OrderStatus, OrderSource

class OrderItemSchema(BaseModel):
    id: int
    ulid: str
    bowl_id: int
    meal_slot: str
    quantity: int
    adjusted_calories: float
    adjusted_macros: Dict[str, Any]
    adjusted_price: float
    adjusted_ingredients: List[Dict[str, Any]]
    
    bowl_name: Optional[str] = None

    class Config:
        from_attributes = True

class OrderCustomerSchema(BaseModel):
    ulid: str
    name: str

class OrderSchema(BaseModel):
    id: int
    ulid: str
    customer_id: int
    plan_id: Optional[int]
    order_source: OrderSource
    status: OrderStatus
    target_date: date
    total_order_price: float
    items: List[OrderItemSchema]
    customer: Optional[OrderCustomerSchema] = None

    class Config:
        from_attributes = True

class OrderListResponse(BaseModel):
    success: bool
    orders: List[OrderSchema]
    total_count: int
    page: int
    limit: int

class OrderPreviewRequest(BaseModel):
    customer_ulid: str
    bowl_ulid: str
    meal_slot: str

class CheckoutIngredient(BaseModel):
    id: Any
    name: str
    macro_tag: str
    original_weight: float
    new_weight: float
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    cost: float

class CheckoutItem(BaseModel):
    meal_slot: str
    bowl_ulid: str
    quantity: int = 1
    
    adjusted_calories: float
    adjusted_protein: float
    adjusted_carbs: float
    adjusted_fat: float
    adjusted_fiber: float
    adjusted_price: float
    
    adjusted_ingredients: List[CheckoutIngredient]

class OrderCheckoutRequest(BaseModel):
    customer_ulid: str
    target_date: date
    items: List[CheckoutItem]
