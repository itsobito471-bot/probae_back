import boto3
from botocore.config import Config
from app.core.config import settings

# Initialize the R2 Client using the secure .env variables
r2_client = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.r2_access_key,
    aws_secret_access_key=settings.r2_secret_key,
    region_name="auto", 
    config=Config(signature_version="s3v4")
)