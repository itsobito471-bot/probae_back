from celery import Celery
from celery.schedules import crontab
import os

# You would normally put these in your settings/environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "probae_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.celery_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=False,
    beat_schedule={
        'generate-daily-orders-noon': {
            'task': 'generate_daily_plan_orders',
            'schedule': crontab(minute=0, hour=12),
        },
    }
)
