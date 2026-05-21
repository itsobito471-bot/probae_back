from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.domains.users.models import User, UserRole
from app.domains.settings.models import SystemSetting, SettingKey
from app.domains.settings.schemas import SettingsPayload

router = APIRouter()

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to manage settings")
    return current_user

@router.get("/", response_model=SettingsPayload)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Fetches all system settings and formats them as a key-value dictionary."""
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    
    # Convert the database rows into a simple JSON dictionary
    return {setting.key.value: setting.value for setting in settings}

@router.put("/", response_model=SettingsPayload)
async def update_settings(
    update_data: SettingsPayload,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Upserts (Updates or Inserts) multiple system settings at once."""
    # 1. Fetch existing settings from the DB
    result = await db.execute(select(SystemSetting))
    existing_settings = {s.key: s for s in result.scalars().all()}

    # 2. Loop through the data the frontend sent (ignoring empty fields)
    for key_str, new_value in update_data.model_dump(exclude_unset=True).items():
        enum_key = SettingKey(key_str)
        
        if enum_key in existing_settings:
            # Update existing
            existing_settings[enum_key].value = str(new_value)
        else:
            # Insert new
            new_setting = SystemSetting(key=enum_key, value=str(new_value))
            db.add(new_setting)

    await db.commit()

    # 3. Return the fresh dictionary
    result = await db.execute(select(SystemSetting))
    updated_settings = result.scalars().all()
    return {s.key.value: s.value for s in updated_settings}