import enum
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from sqlalchemy.orm import relationship

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"
    DELIVERY = "delivery"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Core Identity
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Role & Permissions
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 2FA / Google Authenticator Fields
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_secret: Mapped[str] = mapped_column(String(100), nullable=True)
    
    profile_picture_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=True)
    
    # This relationship lets SQLAlchemy fetch the Document object automatically
    profile_picture = relationship("Document", lazy="joined")
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User {self.email} - {self.role}>"