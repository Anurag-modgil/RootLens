from celery import Celery
from app.config import settings

celery_app = Celery(
    "rootlens_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Configure Celery using settings
celery_app.conf.update(
    task_always_eager=settings.celery_always_eager,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True
)

# Autodiscover tasks in the app folder
celery_app.autodiscover_tasks(["app"])
