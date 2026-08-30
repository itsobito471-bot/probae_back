import asyncio
from fastapi.testclient import TestClient
from main import app
from app.core.security import get_current_user
from app.domains.users.models import User

async def mock_get_current_user():
    user = User()
    user.id = 1
    return user

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)
response = client.get("/api/v1/ingredients/?page=1&page_size=6&sort=A%20to%20Z")
print("Status Code:", response.status_code)
print("Response:", response.text)
