from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    # DELETED: file_url
    size_bytes: int
    created_at: datetime