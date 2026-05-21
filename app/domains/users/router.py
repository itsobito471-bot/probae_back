import random

from fastapi import APIRouter, Depends, HTTPException, Response, status
import jwt
import pyotp
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db, get_redis
from app.core.email import send_otp_email
from app.core.security import get_current_user, get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.domains.users.models import User
from app.domains.users.schemas import ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, RefreshTokenRequest, ResetPasswordRequest, TokenResponse, UserResponse, UserUpdate, Verify2FARequest
from sqlalchemy import or_
router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login_user(
    response: Response, 
    login_data: LoginRequest, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(
            or_(
                User.email == login_data.identifier,
                User.username == login_data.identifier
            )
        )
    )
    user = result.scalars().first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password", # Updated error message
            headers={"WWW-Authenticate": "Bearer"},
        )

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
    result = await db.execute(
        select(User).where(
            or_(
                User.email == request.identifier,
                User.username == request.identifier
            )
        )
    )
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


    redis_key = f"reset_otp:{user.email}"
    await redis.setex(name=redis_key, time=600, value=otp)

    # 4. SEND THE ACTUAL BRANDED EMAIL (We use 'await' so it runs asynchronously)
    try:
        await send_otp_email(email_to=user.email, otp=otp)
    except Exception as e:
        print(f"Failed to send email: {e}")
        # We still return success to the user so we don't expose SMTP errors to the frontend
        return {"message": "If that email exists, an OTP has been sent."}

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


@router.post("/logout")
async def logout(response: Response):
    """
    Clears the HttpOnly refresh token cookie to end the session securely.
    """
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=(settings.environment == "production"),
        samesite="lax",
    )
    
    return {"message": "Successfully logged out"}



@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Allows a logged-in user to change their password by providing their current password.
    """
    # 1. Verify the current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # 2. Prevent setting the same password (optional but good UX)
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as the old password")

    # 3. Hash and save the new password
    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if update_data.profile_picture_id is not None:
        current_user.profile_picture_id = update_data.profile_picture_id
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
        
    await db.commit()
    await db.refresh(current_user)
    return current_user



@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    body: RefreshTokenRequest, 
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decode the token using PyJWT
        payload = jwt.decode(
            body.refresh_token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        # 2. SECURITY: Ensure they are actually sending a "refresh" token
        if user_id_str is None or token_type != "refresh":
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception

    # 3. Verify the user still exists in the database
    result = await db.execute(select(User).where(User.id == int(user_id_str)))
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise credentials_exception

    # 4. Generate a brand new access token
    new_access_token = create_access_token(data={"sub": str(user.id)})

    # 5. Return it
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }