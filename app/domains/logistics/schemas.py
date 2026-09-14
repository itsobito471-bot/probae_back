from pydantic import BaseModel
from typing import Optional, Any, List

class ZoneBase(BaseModel):
    name: str
    polygon_coordinates: Optional[Any] = None
    is_active: bool = True

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    polygon_coordinates: Optional[Any] = None
    is_active: Optional[bool] = None

class ZoneResponse(ZoneBase):
    ulid: str

    class Config:
        from_attributes = True

class DriverBase(BaseModel):
    name: str
    phone: str
    is_active: bool = True

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class DriverResponse(DriverBase):
    ulid: str

    class Config:
        from_attributes = True

class BulkAssignDriverRequest(BaseModel):
    order_ulids: List[str]
    driver_ulid: str

