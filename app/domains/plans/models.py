from sqlalchemy import String, ForeignKey, Integer, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin, generate_ulid

class PlanTier(Base, TimestampMixin):
    __tablename__ = "plan_tiers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    duration: Mapped[str] = mapped_column(String(50), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(255), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    discount_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    selections: Mapped[list["PlanTierSelection"]] = relationship("PlanTierSelection", back_populates="plan_tier", cascade="all, delete-orphan")


class PlanTierSelection(Base):
    __tablename__ = "plan_tier_selections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_tier_id: Mapped[int] = mapped_column(ForeignKey("plan_tiers.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_type_code: Mapped[str] = mapped_column(String(10), nullable=False)
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    bowl_id: Mapped[int] = mapped_column(ForeignKey("bowls.id", ondelete="RESTRICT"), nullable=False, index=True)

    plan_tier: Mapped["PlanTier"] = relationship("PlanTier", back_populates="selections")
    bowl = relationship("Bowl")
