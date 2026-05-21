import boto3
from botocore.config import Config
from app.core.config import settings

# Initialize the R2 Client
r2_client = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.r2_access_key,
    aws_secret_access_key=settings.r2_secret_key,
    region_name="auto", # R2 uses 'auto'
    config=Config(signature_version="s3v4")
)

def get_r2_url(filename: str) -> str:
    """
    Returns the public URL for a file.
    Note: You must make your R2 bucket public in the Cloudflare Dashboard 
    and connect a custom domain (e.g., cdn.probae.com) for this to work perfectly.
    """
    # Replace this with your actual public R2 bucket URL once configured
    return f"https://pub-your-public-r2-url.r2.dev/{filename}"