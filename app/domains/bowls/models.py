import enum
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, Time, Boolean, Numeric, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone, time
from app.core.database import Base, generate_ulid

class BowlType(str, enum.Enum):
    STANDARD = "STANDARD"
    CUSTOM = "CUSTOM"

class BowlSection(str, enum.Enum):
    DRESSING = "Dressing"
    BLENDS = "Blends"
    ADD_ONS = "Add Ons"
    PROTEIN = "Protein"
    CARB = "Carb"
    FIBER = "Fiber"
    EXTRA_PROTEIN = "Extra Protein"

class BowlCategory(Base):
    __tablename__ = "bowl_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    image_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    background_image_filename: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    bowls: Mapped[list["Bowl"]] = relationship("Bowl", back_populates="category", cascade="all, delete-orphan")


class MealCategory(Base):
    __tablename__ = "meal_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color_code: Mapped[str] = mapped_column(String(20), nullable=True)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    
    time_from: Mapped[time] = mapped_column(Time, nullable=True)
    time_to: Mapped[time] = mapped_column(Time, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    bowls: Mapped[list["Bowl"]] = relationship("Bowl", back_populates="meal_category")


class Bowl(Base):
    __tablename__ = "bowls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    bowl_type: Mapped[BowlType] = mapped_column(Enum(BowlType), default=BowlType.STANDARD, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    raw_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    fixed_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    packaging_id: Mapped[int] = mapped_column(ForeignKey("packaging.id", ondelete="SET NULL"), nullable=True)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    
    category_id: Mapped[int] = mapped_column(ForeignKey("bowl_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_category_id: Mapped[int] = mapped_column(ForeignKey("meal_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category: Mapped["BowlCategory"] = relationship("BowlCategory", back_populates="bowls")
    meal_category: Mapped["MealCategory"] = relationship("MealCategory", back_populates="bowls")
    packaging: Mapped["Packaging"] = relationship("Packaging")
    ingredients: Mapped[list["BowlIngredient"]] = relationship("BowlIngredient", back_populates="bowl", cascade="all, delete-orphan")


class BowlIngredient(Base):
    __tablename__ = "bowl_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bowl_id: Mapped[int] = mapped_column(ForeignKey("bowls.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    section_name: Mapped[BowlSection] = mapped_column(Enum(BowlSection), nullable=False)
    weight_g_or_ml: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    bowl: Mapped["Bowl"] = relationship("Bowl", back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient")
