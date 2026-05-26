import json
from jose import jwt
from typing import Callable
from fastapi import Request, Response
from fastapi.routing import APIRoute

# FIX 1: Import AsyncSessionLocal instead of SessionLocal
from app.core.database import AsyncSessionLocal 
from app.core.config import settings
from app.domains.audit.models import AuditLog

class AuditLogRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # 1. Extract JSON Payload (safely)
            payload = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        payload = json.loads(body_bytes)
                except Exception:
                    payload = {"error": "Could not parse body"}

            # 2. Extract User ID from Token (if present)
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    token = auth_header.split(" ")[1]
                    decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                    user_id = int(decoded.get("sub")) if decoded.get("sub") else None
                except Exception:
                    pass

            # 3. Process the actual request
            response: Response = await original_route_handler(request)

            # 4. Save to Database asynchronously
            # FIX 2: Use AsyncSessionLocal here
            async with AsyncSessionLocal() as db: 
                log_entry = AuditLog(
                    user_id=user_id,
                    method=request.method,
                    endpoint=request.url.path,
                    payload=payload,
                    status_code=response.status_code
                )
                db.add(log_entry)
                await db.commit()

            return response

        return custom_route_handler