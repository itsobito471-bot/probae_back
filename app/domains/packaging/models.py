# Backend/app/domains/packaging/models.py
from datetime import datetime, timezone
from sqlalchemy import String, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin, generate_ulid

class PackagingComponent(Base, TimestampMixin):
    __tablename__ = "packaging_components"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)

    # --- Stock Management ---
    current_stock: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default="0.0")
    stock_threshold: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default="0.0")


class Packaging(Base, TimestampMixin):
    __tablename__ = "packaging"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    

    components: Mapped[list["PackagingItemLink"]] = relationship("PackagingItemLink", back_populates="packaging", cascade="all, delete-orphan")

class PackagingItemLink(Base):
    __tablename__ = "packaging_item_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    packaging_id: Mapped[int] = mapped_column(ForeignKey("packaging.id", ondelete="CASCADE"), nullable=False, index=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("packaging_components.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)

    packaging: Mapped["Packaging"] = relationship("Packaging", back_populates="components")
    component: Mapped["PackagingComponent"] = relationship("PackagingComponent")


class PackagingComponentStockLog(Base, TimestampMixin):
    __tablename__ = "packaging_component_stock_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)

    component_id: Mapped[int] = mapped_column(ForeignKey("packaging_components.id", ondelete="CASCADE"), nullable=False, index=True)
    component: Mapped["PackagingComponent"] = relationship("PackagingComponent")

    quantity_change: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    previous_stock: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    new_stock: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=True)
    # Populated when deduction is triggered automatically by an order pack action
    order_ulid: Mapped[str] = mapped_column(String(26), nullable=True)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped["User"] = relationship("User")
