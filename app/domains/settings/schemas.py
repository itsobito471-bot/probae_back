from pydantic import BaseModel, ConfigDict
from typing import Optional

class SettingsPayload(BaseModel):
    
    # Map directly to your Enum keys
    R2_BASE_URL: Optional[str] = None
    MAINTENANCE_MODE: Optional[str] = None
    SUPPORT_EMAIL: Optional[str] = None

    # This ensures if the frontend sends a random key, FastAPI just ignores it
    model_config = ConfigDict(extra="ignore")