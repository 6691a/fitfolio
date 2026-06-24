from celery import Celery

from app.config.containers import Container
from app.config.settings import settings

celery_app = Celery(
    "fitfolio",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.autodiscover_tasks(["app"])

container = Container()
container.wire(modules=["app.tasks.documents"])
