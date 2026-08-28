import asyncio
import logging
from app.core.celery_app import celery_app
from app.tasks.generate_plan_orders import generate_daily_orders

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

@celery_app.task(name="create_calorie_log_on_dispatch")
def task_create_calorie_log_on_dispatch(order_ulid: str, customer_ulid: str):
    """
    Example event-driven task: When an order is DISPATCHED, we drop this task into Celery.
    Celery will process it in the background to create a calorie log for the customer,
    ensuring the main API response remains lightning fast.
    """
    logger.info(f"Celery Task: Creating calorie log for order {order_ulid} (Customer: {customer_ulid})")
    
    # Example pseudo-code for async execution:
    # async def _create_log():
    #     async with async_session_maker() as db:
    #         # ... create log logic ...
    #         await db.commit()
    #
    # asyncio.run(_create_log())
    pass
