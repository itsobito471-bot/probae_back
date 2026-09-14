from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .models import TransactionType

class TransactionCreateRequest(BaseModel):
    amount: float
    method: str
    description: str

class TransactionResponse(BaseModel):
    ulid: str
    transaction_type: TransactionType
    amount: float
    reference_id: Optional[str] = None
    description: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total_count: int
