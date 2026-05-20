from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.core.config import settings

# Configure the SMTP connection
conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email_to: EmailStr, otp: str):
    """Generates the Probae branded HTML email and sends it."""
    
    # Probae Branded HTML Template
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        
        <div style="background-color: #59178A; padding: 25px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: bold; letter-spacing: 1px;">probae<span style="color: #6BA855;">.</span></h1>
        </div>
        
        <div style="padding: 40px 30px; text-align: center; background-color: #ffffff;">
            <h2 style="color: #333333; margin-top: 0;">Password Reset Request</h2>
            <p style="color: #666666; font-size: 16px; line-height: 1.5;">
                We received a request to reset the password for your Probae account. Please use the verification code below to securely change your password.
            </p>
            
            <div style="margin: 40px 0;">
                <span style="font-size: 36px; font-weight: bold; color: #59178A; letter-spacing: 8px; background-color: #f8f9fa; padding: 15px 30px; border-radius: 8px; border-bottom: 4px solid #6BA855;">
                    {otp}
                </span>
            </div>
            
            <p style="color: #999999; font-size: 14px; margin-bottom: 0;">
                This code is valid for 10 minutes. If you did not request a password reset, you can safely ignore this email.
            </p>
        </div>
        
    </div>
    """

    message = MessageSchema(
        subject="Probae - Your Password Reset Code",
        recipients=[email_to],
        body=html_content,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)