from celery import Celery

from app.core.config import settings

celery_app = Celery("reklaim")

celery_app.config_from_object(
    {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
        "task_track_started": True,
    }
)

celery_app.autodiscover_tasks(["app.worker"])
