import asyncio
import logging
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.tasks.generate_plan_orders import generate_daily_orders

# ── CRITICAL: import ALL domain models at startup so SQLAlchemy's mapper
# registry is fully populated before any query is executed.
# Without this, lazy string references like relationship("Document") fail
# because the Celery worker process never loaded that model.
import app.domains.audit.models          # noqa: F401
import app.domains.bowls.models          # noqa: F401
import app.domains.customers.models      # noqa: F401
import app.domains.documents.models      # noqa: F401
import app.domains.ingredients.models    # noqa: F401
import app.domains.inventory.models      # noqa: F401
import app.domains.orders.models         # noqa: F401
import app.domains.packaging.models      # noqa: F401
import app.domains.plans.models          # noqa: F401
import app.domains.raw_materials.models  # noqa: F401
import app.domains.settings.models       # noqa: F401
import app.domains.users.models          # noqa: F401
import app.domains.vendors.models        # noqa: F401

# Now it is safe to reference these classes directly
from app.domains.orders.models import Order
from app.domains.customers.models import Customer, CustomerCalorieLog

logger = logging.getLogger(__name__)

# Note: Celery is synchronous by default. Since our backend uses SQLAlchemy AsyncIO,
# we need to wrap async functions in asyncio.run() when calling them from Celery tasks.

@celery_app.task(name="generate_daily_plan_orders")
def task_generate_daily_orders():
    """
    Celery task that triggers the daily plan order generation.
    Can be run via Celery Beat or triggered manually via API/aaPanel.
    """
    logger.info("Celery Task: Starting daily order generation...")
    # Run the async logic
    asyncio.run(generate_daily_orders())
    logger.info("Celery Task: Daily order generation complete.")



@celery_app.task(name="create_calorie_log_on_delivery")
def task_create_calorie_log_on_delivery(order_ulid: str):
    logger.info(f"Celery Task: Processing calorie logs for delivered order {order_ulid}")

    async def _process_logs():
        async with AsyncSessionLocal() as db:
            order = await db.scalar(
                select(Order).options(selectinload(Order.items)).where(Order.ulid == order_ulid)
            )
            if not order:
                logger.error(f"Order {order_ulid} not found in DB.")
                return

            customer = await db.scalar(select(Customer).where(Customer.id == order.customer_id))
            if not customer:
                logger.error(f"Customer for order {order_ulid} not found.")
                return

            total_added_cals = 0.0
            for item in order.items:
                log = CustomerCalorieLog(
                    customer_id=order.customer_id,
                    order_id=order.id,
                    target_date=order.target_date,
                    meal_slot=item.meal_slot,
                    calories=item.adjusted_calories,
                    protein=item.adjusted_macros.get("protein", 0.0) if item.adjusted_macros else 0.0,
                    carbs=item.adjusted_macros.get("carbs", 0.0) if item.adjusted_macros else 0.0,
                    fat=item.adjusted_macros.get("fat", 0.0) if item.adjusted_macros else 0.0,
                    fiber=item.adjusted_macros.get("fiber", 0.0) if item.adjusted_macros else 0.0,
                )
                db.add(log)
                total_added_cals += float(item.adjusted_calories)

            # Update customer lifetime total
            customer.total_calories_ordered = float(customer.total_calories_ordered or 0.0) + total_added_cals

            await db.commit()
            logger.info(
                f"Logged {len(order.items)} items (+{total_added_cals} kcal) for customer {customer.ulid}."
            )

    asyncio.run(_process_logs())
