from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from redis import asyncio as aioredis

# 1. Create the asynchronous engine
engine = create_async_engine(
    settings.database_url,
    echo=(settings.environment == "development"),  # Logs SQL only in dev
    future=True
)

# 2. Create an async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


from ulid import ULID

def generate_ulid() -> str:
    return str(ULID())

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

# 3. Create the declarative base for your models
class Base(DeclarativeBase):

    pass

async def get_redis():
    yield redis_client

from app.domains.users.models import User

# 4. Dependency injector to get a DB session per request
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()