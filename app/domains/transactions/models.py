import enum
from sqlalchemy import String, ForeignKey, Numeric, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin, generate_ulid

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    DEBIT = "DEBIT"
    REFUND = "REFUND"

class TransactionLedger(Base, TimestampMixin):
    __tablename__ = "transaction_ledgers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    customer = relationship("Customer")
