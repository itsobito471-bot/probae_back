from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    file_url: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}