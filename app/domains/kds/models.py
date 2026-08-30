import enum
from datetime import date
from sqlalchemy import String, Enum, Integer, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin

class PrepStatus(str, enum.Enum):
    UNCOOKED = "UNCOOKED"
    PREPARING = "PREPARING"
    PREPARED = "PREPARED"

class DailyPrepTask(Base, TimestampMixin):
    __tablename__ = "daily_prep_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[PrepStatus] = mapped_column(Enum(PrepStatus), default=PrepStatus.UNCOOKED, nullable=False)

    __table_args__ = (
        UniqueConstraint('target_date', 'ingredient_id', name='uix_target_date_ingredient'),
    )

    ingredient = relationship("Ingredient")
