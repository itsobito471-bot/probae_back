from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext

from app.domains.users.models import User, UserRole
from app.domains.documents.models import Document

# Setup password hashing locally for this domain
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def seed_users(db: AsyncSession):
    """Handles all user-related database seeding."""
    print("⏳ Seeding Users Domain...")
    admin_email = "admin@probae.com"
    username = "probae_admin"
    
    # Check if admin exists to prevent duplicates
    result = await db.execute(select(User).where(User.email == admin_email, User.username == username))
    existing_admin = result.scalars().first()
    
    if existing_admin:
        print(f"  -> ✅ Admin already exists ({admin_email}). Skipping.")
        return

    # If not, create them
    new_admin = User(
        username=username,
        email=admin_email,
        password_hash=get_password_hash("SuperSecretPassword123!"),
        full_name="System Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(new_admin)
    print(f"  -> ✅ Admin created successfully! ({admin_email})")