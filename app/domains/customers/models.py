import enum
from sqlalchemy import String, Boolean, Enum, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin, generate_ulid

class CustomerStatus(str, enum.Enum):
    ONBOARDING = "ONBOARDING"
    PENDING_PLAN = "PENDING_PLAN"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)

    # Basic Info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Biological Info
    sex: Mapped[str] = mapped_column(String(10), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[float] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Integer, nullable=False)
    activity_level: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Dietary Profile
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    dietary_preferences: Mapped[dict] = mapped_column(JSON, nullable=True)
    allergies: Mapped[dict] = mapped_column(JSON, nullable=True)
    chef_instructions: Mapped[str] = mapped_column(String(1000), nullable=True)
    
    # Calculated Profile
    calorie_profile: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # Plan
    selected_plan_id: Mapped[str] = mapped_column(String(26), ForeignKey("plan_tiers.ulid"), nullable=True)
    
    # Status
    status: Mapped[CustomerStatus] = mapped_column(Enum(CustomerStatus), default=CustomerStatus.ONBOARDING, nullable=False)

    def __repr__(self):
        return f"<Customer {self.name} - {self.phone}>"
