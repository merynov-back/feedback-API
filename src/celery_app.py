from celery import Celery
from src.config import settings


celery_app = Celery(
    "feedback_api",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.email_tasks"],
)

celery_app.conf.update(
    # Сериализация задач и результатов через JSON
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Тайм зона, в которой работает Celery
    timezone="UTC",
    enable_utc=True,

    # Подтверждение получения задачи 
    task_ack_late=True,

    task_reject_on_worker_lost=True,

    # TTL для результатов в Backend - 1 день
    result_expires=86_400,
)