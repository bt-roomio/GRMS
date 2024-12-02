import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

RABBIT_LOGIN = settings.RABBIT_LOGIN
RABBIT_PASSWORD = settings.RABBIT_PASSWORD
RABBIT_HOST = settings.RABBIT_HOST
RABBIT_PORT = settings.RABBIT_PORT

CELERY_BROKER_URL = f"amqp://{RABBIT_LOGIN}:{RABBIT_PASSWORD}@{RABBIT_HOST}:{RABBIT_PORT}//"

app = Celery("config", broker=CELERY_BROKER_URL)

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
