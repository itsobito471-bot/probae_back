import enum
from sqlalchemy import String, ForeignKey, Numeric, Date, Enum, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from app.core.database import Base, TimestampMixin, generate_ulid

class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    PREPARED = "PREPARED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class OrderSource(str, enum.Enum):
    CUSTOM = "CUSTOM"
    PLAN = "PLAN"

class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plan_tiers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    order_source: Mapped[OrderSource] = mapped_column(Enum(OrderSource), default=OrderSource.PLAN, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_order_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)

    # Relationships
    customer = relationship("Customer")
    plan = relationship("PlanTier")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    bowl_id: Mapped[int] = mapped_column(ForeignKey("bowls.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    meal_slot: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Frozen snapshot of the customized scaling engine output
    adjusted_calories: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    adjusted_macros: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    adjusted_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    adjusted_ingredients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    bowl = relationship("Bowl")
