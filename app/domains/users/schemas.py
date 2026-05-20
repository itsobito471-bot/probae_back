
from typing import Optional

from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None  # Make this optional for the first step of login

class Verify2FARequest(BaseModel):
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class Verify2FARequest(BaseModel):
    code: str



class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    role: str
    two_factor_enabled: bool

    # This tells Pydantic to read the data directly from the SQLAlchemy model
    model_config = {"from_attributes": True}