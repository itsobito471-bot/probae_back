from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from .models import PrepStatus

# Prep List Schemas
class PrepRawMaterial(BaseModel):
    raw_material_id: int
    name: str
    total_weight_needed: float
    unit: str = "g" # Assuming everything is g or ml

class PrepComponent(BaseModel):
    ingredient_id: int
    name: str
    total_weight_needed: float
    status: PrepStatus
    raw_materials: List[PrepRawMaterial]

class PrepListResponse(BaseModel):
    target_date: date
    total_bowls: int
    components: List[PrepComponent]

class PrepStatusUpdateRequest(BaseModel):
    status: PrepStatus

# Assembly List Schemas
class AssemblyComponent(BaseModel):
    ingredient_id: int
    name: str
    weight_needed: float

class AssemblyBowl(BaseModel):
    bowl_id: int
    bowl_name: str
    packaging_name: Optional[str]
    quantity: int
    components: List[AssemblyComponent]

class AssemblyListResponse(BaseModel):
    target_date: date
    total_bowls: int
    bowls: List[AssemblyBowl]
