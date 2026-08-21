from __future__ import annotations

from celery import Task, shared_task
from celery.utils.log import get_task_logger
from kombu.exceptions import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from structlog.contextvars import bind_contextvars, get_contextvars

logger = get_task_logger(__name__)


class CorrelatedTask(Task):
    autoretry_for = (
        ConnectionError,
        TimeoutError,
        OperationalError,
        RedisConnectionError,
        RedisTimeoutError,
    )
    retry_backoff = True
    retry_backoff_max = 600
    retry_kwargs = {"max_retries": 5}
    acks_late = True
    reject_on_worker_lost = True

    def apply_async(self, args=None, kwargs=None, **options):
        headers = options.setdefault("headers", {})
        correlation_id = get_contextvars().get("correlation_id")
        if correlation_id:
            headers["correlation_id"] = correlation_id
        return super().apply_async(args, kwargs, **options)

    def __call__(self, *args, **kwargs):
        if self.request.headers and self.request.headers.get("correlation_id"):
            bind_contextvars(correlation_id=self.request.headers["correlation_id"])
        return super().__call__(*args, **kwargs)


@shared_task(base=CorrelatedTask, name="apps.core.tasks.maintenance_heartbeat")
def maintenance_heartbeat():
    logger.info("maintenance_heartbeat")
