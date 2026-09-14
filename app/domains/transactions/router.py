from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.domains.customers.models import Customer
from .models import TransactionLedger, TransactionType
from .schemas import TransactionCreateRequest, TransactionListResponse, TransactionResponse

router = APIRouter(prefix="/customers/{customer_ulid}/transactions", tags=["Transactions"])

@router.post("", response_model=TransactionResponse)
async def log_payment(
    customer_ulid: str,
    req: TransactionCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    customer = await db.scalar(select(Customer).where(Customer.ulid == customer_ulid))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Log DEPOSIT
    tx = TransactionLedger(
        customer_id=customer.id,
        transaction_type=TransactionType.DEPOSIT,
        amount=req.amount,
        reference_id=f"PAY_{req.method.upper()}",
        description=req.description
    )
    db.add(tx)
    
    # Update balance
    customer.wallet_balance = float(customer.wallet_balance or 0.0) + req.amount
    
    await db.commit()
    await db.refresh(tx)
    
    return tx

@router.get("", response_model=TransactionListResponse)
async def get_transactions(
    customer_ulid: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    customer = await db.scalar(select(Customer).where(Customer.ulid == customer_ulid))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    query = select(TransactionLedger).where(TransactionLedger.customer_id == customer.id)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    items_query = query.order_by(desc(TransactionLedger.created_at)).offset((page - 1) * limit).limit(limit)
    items_res = await db.scalars(items_query)
    items = items_res.all()
    
    return TransactionListResponse(
        transactions=items,
        total_count=total_count
    )
