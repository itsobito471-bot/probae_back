import random

from fastapi import APIRouter, Depends, HTTPException, Response, status
import pyotp
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db, get_redis
from app.core.security import get_current_user, get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.domains.users.models import User
from app.domains.users.schemas import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, TokenResponse, UserResponse, Verify2FARequest

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login_user(
    response: Response, 
    login_data: LoginRequest, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    # --- 2FA ENFORCEMENT BLOCK ---
    if user.two_factor_enabled:
        if not login_data.totp_code:
            # Tell the frontend to prompt the user for their 6-digit code
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="2FA verification required"
            )
        
        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(login_data.totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    # -----------------------------

    token_payload = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)

    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, 
        secure=(settings.environment == "production"), samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60
    )

    return TokenResponse(access_token=access_token, role=user.role.value)



@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest, 
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis) # Inject Redis
):
    # 1. Find the user in Postgres
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()

    # Even if user doesn't exist, return success to prevent email enumeration
    if not user:
        return {"message": "If that email exists, an OTP has been sent."}

    # 2. Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # 3. Save to Redis with a 10-minute (600 seconds) Time-To-Live (TTL)
    # We use the email as the unique key prefix (e.g., "reset_otp:admin@probae.com")
    redis_key = f"reset_otp:{user.email}"
    await redis.setex(name=redis_key, time=600, value=otp)

    # 4. TODO: Send actual email via SMTP.
    print(f"\n📧 EMAIL MOCK: Sending OTP {otp} to {user.email} (Stored in Redis)\n")

    return {"message": "If that email exists, an OTP has been sent."}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest, 
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis) # Inject Redis
):
    # 1. Check Redis for the OTP
    redis_key = f"reset_otp:{request.email}"
    stored_otp = await redis.get(redis_key)

    # 2. Validate OTP
    if not stored_otp or stored_otp != request.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # 3. Find the user in Postgres to update their password
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()

    if not user:
         raise HTTPException(status_code=400, detail="User not found")

    # 4. Hash new password and save to Postgres
    user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    # 5. Delete the OTP from Redis immediately so it can't be reused
    await redis.delete(redis_key)

    return {"message": "Password has been reset successfully"}


@router.post("/setup-2fa")
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    # Generate a random Base32 secret
    secret = pyotp.random_base32()
    print(secret)  # For debugging - in production, you wouldn't log this!
    
    # Save it to the database, but keep 'enabled' as False until they verify it
    current_user.two_factor_secret = secret
    await db.commit()

    # Generate the URI that the frontend will use to draw the QR Code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email, 
        issuer_name="ProBae Admin"
    )

    return {
        "secret": secret,
        "qr_code_url": provisioning_uri,
        "message": "Scan this with Google Authenticator and verify the code."
    }


@router.post("/verify-2fa")
async def verify_2fa(
    request: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    if not current_user.two_factor_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated")

    # Verify the 6-digit code against their specific secret
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(request.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    # Lock it in
    current_user.two_factor_enabled = True
    await db.commit()

    return {"message": "2FA successfully enabled!"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the currently logged-in user's profile data.
    Requires a valid Access Token in the Authorization header.
    """
    # The get_current_user dependency already fetched the user from the DB!
    return current_user