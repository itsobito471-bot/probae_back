import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Numeric, Enum, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, generate_ulid

class UnitType(str, enum.Enum):
    KG = "kg"
    L = "l"
    G = "g"
    ML = "ml"

class RawMaterialCategory(Base):
    __tablename__ = "raw_material_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class RawMaterial(Base):
    __tablename__ = "raw_materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    item_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[UnitType] = mapped_column(Enum(UnitType), nullable=False)
    
    category_id: Mapped[int] = mapped_column(ForeignKey("raw_material_categories.id", ondelete="SET NULL"), nullable=True)
    category = relationship("RawMaterialCategory")
    
    # --- Images ---
    image_filename: Mapped[str] = mapped_column(String(255), nullable=True) # Primary/Thumbnail
    background_image_filename: Mapped[str] = mapped_column(String(255), nullable=True) # Detail View Background
    
    # --- Stock Management ---
    current_stock: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default="0.0")
    stock_threshold: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default="0.0")
    
    # --- Nutritional Profile ---
    calories: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    protein: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    carbs: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    fiber: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    fat: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Stored as a JSON Array (e.g., ["Vitamin B12", "Iron"])
    micros: Mapped[list[str]] = mapped_column(JSON, nullable=True)
    
    # --- Audit & Relations ---
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class RawMaterialStockLog(Base):
    __tablename__ = "raw_material_stock_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    
    raw_material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_material = relationship("RawMaterial")
    
    quantity_change: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    previous_stock: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    new_stock: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))