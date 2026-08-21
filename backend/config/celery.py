import os

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
app = Celery("portfolio")
app.config_from_object("django.conf:settings", namespace="CELERY")
exchange = Exchange("portfolio", type="direct")
app.conf.task_queues = tuple(
    Queue(
        name,
        exchange=exchange,
        routing_key=name,
        queue_arguments={
            "x-dead-letter-exchange": "portfolio.dlx",
            "x-dead-letter-routing-key": "dead",
        },
    )
    for name in ("pdf", "email", "analytics", "media", "billing", "maintenance")
) + (Queue("dead", exchange=Exchange("portfolio.dlx", type="direct"), routing_key="dead"),)
app.conf.task_default_queue = "maintenance"
app.conf.beat_schedule = {
    "maintenance-heartbeat": {
        "task": "apps.core.tasks.maintenance_heartbeat",
        "schedule": crontab(minute="*/5"),
    }
}
app.autodiscover_tasks()
