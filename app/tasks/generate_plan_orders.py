import asyncio
import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.domains.customers.models import Customer
from app.domains.plans.models import PlanTier, PlanTierSelection
from app.domains.bowls.models import Bowl, BowlIngredient
from app.domains.orders.models import Order, OrderItem, OrderSource, OrderStatus
from app.domains.orders.scaling_service import scale_bowl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_daily_orders():
    logger.info("Starting daily automated plan order generation.")
    
    tomorrow = date.today() + timedelta(days=1)
    day_index = tomorrow.weekday() # 0 = Monday, 6 = Sunday
    logger.info(f"Target Date: {tomorrow}, Target Day Index: {day_index}")
    
    # Mapping for DB Plan code to Customer mealSlot key
    code_map = {
        "B": "B-FAST",
        "L": "LUNCH",
        "D": "DINNER"
    }

    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch active customers with assigned plans
            customers = await db.scalars(
                select(Customer)
                .where(
                    Customer.status == "ACTIVE",
                    Customer.selected_plan_id.isnot(None)
                )
            )
            customers = customers.all()
            logger.info(f"Found {len(customers)} active customers on a subscription plan.")
            
            for customer in customers:
                try:
                    logger.info(f"Processing Customer ULID: {customer.ulid}")
                    # Prepare customer metrics
                    calorie_profile = customer.calorie_profile or {}
                    meal_calories = calorie_profile.get("mealCalories", {})
                    goal = customer.goal or "MAINTENANCE"
                    
                    # 2. Fetch PlanTier and Selections for tomorrow
                    plan = await db.scalar(
                        select(PlanTier)
                        .where(PlanTier.ulid == customer.selected_plan_id, PlanTier.is_deleted == False)
                        .options(
                            selectinload(PlanTier.selections).selectinload(PlanTierSelection.bowl).selectinload(Bowl.ingredients).selectinload(BowlIngredient.ingredient)
                        )
                    )
                    
                    if not plan:
                        logger.warning(f"Plan {customer.selected_plan_id} for customer {customer.ulid} not found or deleted. Skipping.")
                        continue
                        
                    # Filter selections for tomorrow
                    tomorrow_selections = [sel for sel in plan.selections if sel.day_index == day_index]
                    
                    if not tomorrow_selections:
                        logger.info(f"Customer {customer.ulid} has no meals scheduled for tomorrow (day {day_index}).")
                        continue
                        
                    gross_price = 0.0
                    order_items_to_create = []
                    
                    # 3. Process each bowl in the schedule
                    for sel in tomorrow_selections:
                        mapped_key = code_map.get(sel.meal_type_code, sel.meal_type_code)
                        target_calories = float(meal_calories.get(mapped_key, 0.0))
                        bowl = sel.bowl
                        
                        if not bowl or not bowl.ingredients or target_calories <= 0:
                            logger.warning(f"Skipping bowl for customer {customer.ulid} (missing bowl/ingredients or 0 target calories).")
                            continue
                            
                        # Pass through scaling engine
                        scaled_result = await scale_bowl(bowl, target_calories, goal)
                        
                        # Prepare the snapshot for the database
                        order_items_to_create.append(
                            OrderItem(
                                bowl_id=bowl.id,
                                meal_slot=mapped_key,
                                adjusted_calories=scaled_result.total_calories,
                                adjusted_macros={
                                    "protein": scaled_result.total_protein,
                                    "carbs": scaled_result.total_carbs,
                                    "fat": scaled_result.total_fat,
                                    "fiber": scaled_result.total_fiber
                                },
                                adjusted_price=scaled_result.final_price,
                                adjusted_ingredients=[ing.dict() for ing in scaled_result.ingredients]
                            )
                        )
                        gross_price += scaled_result.final_price

                    if order_items_to_create:
                        # 4. Create the final Order wrapper
                        # (Applying discount percentage could be done here based on Plan logic, 
                        #  but as per requirements we use total adjusted gross price, or if specific plan pricing applies, we adjust.)
                        # Usually, subscription bowls might just cost the adjusted price, or the plan is prepaid.
                        # For now, we store the pure gross scaled price.
                        
                        new_order = Order(
                            customer_id=customer.id,
                            plan_id=plan.id,
                            order_source=OrderSource.PLAN,
                            status=OrderStatus.CREATED,
                            target_date=tomorrow,
                            total_order_price=gross_price
                        )
                        
                        # Attach items
                        new_order.items = order_items_to_create
                        
                        db.add(new_order)
                        logger.info(f"Created Order for customer {customer.ulid} for {tomorrow} with {len(order_items_to_create)} items.")
                    
                except Exception as e:
                    logger.error(f"Failed processing customer {customer.ulid}: {e}")
                    continue # Ensure one bad customer doesn't crash the whole batch
            
            # Commit the transaction once for all customers
            await db.commit()
            logger.info("Batch generation committed successfully.")
            
        except Exception as e:
            logger.error(f"Critical failure during batch run: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(generate_daily_orders())
