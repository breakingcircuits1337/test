import os
from celery import Celery
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend_url = os.getenv("CELERY_RESULT_BACKEND", broker_url)
celery_app = Celery('ada', broker=broker_url, backend=backend_url)
celery_app.conf.update(task_serializer='pickle', result_serializer='pickle', accept_content=['pickle','json'])