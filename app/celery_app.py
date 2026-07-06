from celery import Celery

from app.ai import vision
from app.ai.classification.document import langchain as classifier_langchain
from app.ai.extraction import langchain as extraction_langchain
from app.config.containers import Container
from app.config.settings import settings

celery_app = Celery(
    "fitfolio",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.autodiscover_tasks(["app"])

container = Container()
container.wire(
    modules=["app.tasks.documents", "app.tasks.analyses", classifier_langchain, extraction_langchain, vision]
)
