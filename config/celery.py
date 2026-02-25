import os

from celery import Celery
from celery.schedules import crontab


env = os.getenv("DJANGO_ENV", "development")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{env}")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "expire-pending-payments-every-minute": {
        "task": "django_app.app_payments.tasks.expire_pending_payments_task",
        "schedule": crontab(minute="*"),
    },
}
