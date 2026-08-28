from celery import Celery
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
    timezone="UTC",
    enable_utc=True,
    # Example Celery Beat schedule configuration:
    # beat_schedule={
    #     'generate-daily-orders-midnight': {
    #         'task': 'app.tasks.celery_tasks.task_generate_daily_orders',
    #         'schedule': crontab(minute=0, hour=0),
    #     },
    # }
)
