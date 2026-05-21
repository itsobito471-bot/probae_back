
from typing import Optional

from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    identifier: str
    password: str
    totp_code: Optional[str] = None  # Make this optional for the first step of login

class Verify2FARequest(BaseModel):
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ForgotPasswordRequest(BaseModel):
    identifier: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class Verify2FARequest(BaseModel):
    code: str



class ProfilePictureResponse(BaseModel):
    id: int
    filename: str # <-- Changed from file_url

    model_config = {"from_attributes": True}

# 2. Update your UserResponse
class UserResponse(BaseModel):
    id: int
    username: str # (Assuming you still have this from our dual-login update!)
    email: EmailStr
    full_name: str | None = None
    role: str
    two_factor_enabled: bool
    
    # 3. Add the nested relationship right here
    profile_picture: Optional[ProfilePictureResponse] = None 

    model_config = {"from_attributes": True}



class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserUpdate(BaseModel):
    profile_picture_id: int | None = None
    full_name: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str

