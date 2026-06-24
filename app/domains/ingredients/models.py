import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Numeric, Enum, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, generate_ulid

class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # --- Images ---
    image_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    background_image_filename: Mapped[str] = mapped_column(String(255), nullable=True)

    # --- Aggregates (calculated dynamically from raw materials) ---
    total_weight: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_calories: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_protein: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_carbs: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_fat: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_fiber: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    # --- Audit & Relations ---
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    raw_materials: Mapped[list["IngredientRawMaterial"]] = relationship("IngredientRawMaterial", back_populates="ingredient", cascade="all, delete-orphan")


class IngredientRawMaterial(Base):
    __tablename__ = "ingredient_raw_materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Specific weight used in this ingredient (in grams or ml)
    weight_g_or_ml: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="raw_materials")
    raw_material: Mapped["RawMaterial"] = relationship("RawMaterial") # Make sure RawMaterial is imported or string ref is valid. 
