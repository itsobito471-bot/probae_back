from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class VendorBase(BaseModel):
    name: str
    description: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class VendorResponse(VendorBase):
    id: int
    ulid: str
    code: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedVendorResponse(BaseModel):
    items: List[VendorResponse]
    total: int
    page: int
    page_size: int
    pages: int
