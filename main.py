from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import get_db

from app.domains.users.router import router as users_router
from app.domains.customers.router import router as customers_router

from app.domains.documents.router import router as documents_router
from app.domains.settings.router import router as settings_router
from app.domains.raw_materials.router import router as raw_materials_router
from app.domains.raw_materials.category_router import router as raw_materials_category_router
from app.domains.ingredients.router import router as ingredients_router
from app.domains.bowls.router import router as bowls_router
from app.domains.bowls.meal_category_router import router as meal_category_router
from app.domains.packaging.router import router as packaging_router
from app.domains.bowls.bowl_router import router as bowl_main_router
from app.domains.vendors.router import router as vendors_router
from app.domains.plans.router import router as plans_router
from app.domains.orders.router import router as orders_router

app = FastAPI(
    title=settings.app_name,
    description="Modular backend API for personalized tiered bowl meal prep and pre-orders.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # Allow your Next.js frontend origin
    allow_origins=["http://localhost:3000","http://localhost:3001"], 
    
    # CRITICAL: Must be True so the frontend can receive the HttpOnly Refresh Token Cookie!
    allow_credentials=True, 
    
    # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS)
    allow_methods=["*"], 
    
    # Allow all headers (Authorization, Content-Type, etc.)
    allow_headers=["*"], 
)

# TODO: We will include our domain routers here later like this:
# from app.domains.inventory import router as inventory_router
# app.include_router(inventory_router.router, prefix="/api/v1/inventory", tags=["Inventory"])

app.include_router(users_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(customers_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(settings_router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(raw_materials_category_router, prefix="/api/v1/raw-material-categories", tags=["Raw Material Categories"])
app.include_router(raw_materials_router, prefix="/api/v1/raw-materials", tags=["Raw Materials"])
app.include_router(ingredients_router, prefix="/api/v1/ingredients", tags=["Ingredients"])
app.include_router(bowls_router, prefix="/api/v1/bowl-categories", tags=["Bowl Categories"])
app.include_router(meal_category_router, prefix="/api/v1/meal-categories", tags=["Meal Categories"])
app.include_router(packaging_router, prefix="/api/v1/packaging", tags=["Packaging"])
app.include_router(bowl_main_router, prefix="/api/v1/bowls", tags=["Bowls"])
app.include_router(vendors_router, prefix="/api/v1/vendors", tags=["Vendors"])
app.include_router(plans_router, prefix="/api/v1/plans", tags=["Plan Tiers"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}. Systems are operational."}

@app.get("/health-check")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Verifies that the API can successfully communicate with PostgreSQL."""
    try:
        result = await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "environment": settings.environment
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )