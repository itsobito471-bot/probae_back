import enum
from sqlalchemy import String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

# 1. Hardcode your allowed keys here. 
# Add as many as you want in the future without changing the DB!
class SettingKey(str, enum.Enum):
    R2_BASE_URL = "R2_BASE_URL"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"
    SUPPORT_EMAIL = "SUPPORT_EMAIL"

class SystemSetting(Base):
    __tablename__ = "system_settings"

    # The Key becomes the Primary Key
    key: Mapped[SettingKey] = mapped_column(Enum(SettingKey), primary_key=True, index=True)
    
    # The Value is Text (so it can store long URLs, JSON strings, or simple booleans)
    value: Mapped[str] = mapped_column(Text, nullable=True)