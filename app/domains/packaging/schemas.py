from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# Packaging Component Schemas
class PackagingComponentBase(BaseModel):
    name: str
    cost: float

class PackagingComponentCreate(PackagingComponentBase):
    pass

class PackagingComponentUpdate(BaseModel):
    name: Optional[str] = None
    cost: Optional[float] = None

class PackagingComponentResponse(PackagingComponentBase):
    id: int
    ulid: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedPackagingComponentResponse(BaseModel):
    items: List[PackagingComponentResponse]
    total: int
    page: int
    page_size: int
    pages: int

# Packaging Link Schemas
class PackagingItemLinkInput(BaseModel):
    component_ulid: str
    quantity: int

class PackagingItemLinkResponse(BaseModel):
    component: PackagingComponentResponse
    quantity: int
    
    model_config = ConfigDict(from_attributes=True)

# Packaging Schemas
class PackagingBase(BaseModel):
    name: str
    code: Optional[str] = None

class PackagingCreate(PackagingBase):
    components: List[PackagingItemLinkInput] = []

class PackagingUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    components: Optional[List[PackagingItemLinkInput]] = None

class PackagingResponse(PackagingBase):
    id: int
    ulid: str
    total_cost: float
    components: List[PackagingItemLinkResponse] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedPackagingResponse(BaseModel):
    items: List[PackagingResponse]
    total: int
    page: int
    page_size: int
    pages: int
