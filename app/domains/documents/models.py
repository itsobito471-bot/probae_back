from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin, generate_ulid

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ulid: Mapped[str] = mapped_column(String(26), default=generate_ulid, unique=True, index=True, nullable=False)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # DELETED: file_url column
    
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)