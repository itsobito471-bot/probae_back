import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.storage import r2_client, get_r2_url
from app.domains.documents.models import Document
from app.domains.documents.schemas import DocumentResponse
from app.domains.users.models import User

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Generate a unique filename to prevent overwriting
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # 2. Upload to Cloudflare R2
        # We run this in a threadpool because boto3 is synchronous
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: r2_client.upload_fileobj(
                file.file, 
                settings.r2_bucket_name, 
                unique_filename,
                ExtraArgs={"ContentType": file.content_type}
            )
        )

        # 3. Create the database record
        # Note: You have to calculate size or rely on the frontend payload, 
        # but for safety, we check the spool length
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0) # Reset pointer

        new_doc = Document(
            filename=unique_filename,
            content_type=file.content_type,
            file_url=get_r2_url(unique_filename),
            size_bytes=file_size
        )
        
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        return new_doc

    except Exception as e:
        print(f"R2 Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")