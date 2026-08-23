from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin, generate_ulid

def generate_vendor_code():
    return f"VND-{generate_ulid()[:6].upper()}"

class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), default=generate_vendor_code, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
